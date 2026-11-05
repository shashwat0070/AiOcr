"""Evaluate local extraction against labeled synthetic invoices; no API calls."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import platform
import statistics
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.doc_ai.config import Settings
from src.doc_ai.pipeline import DocumentPipeline

FIELDS = {"vendor_name", "invoice_number", "invoice_date", "due_date",
          "subtotal", "tax", "shipping_handling", "total_amount"}
MODES = ("rule-based", "adaptive-local")
DEFAULT_MANIFEST = ROOT / "examples" / "benchmark" / "manifest.json"


def values_match(actual, expected):
    """Compare amounts within one cent; text ignores case/whitespace only."""
    if expected is None:
        return actual is None or actual == ""
    if isinstance(expected, (int, float)) and not isinstance(expected, bool):
        try:
            return not isinstance(actual, bool) and math.isclose(
                float(actual), expected, rel_tol=0, abs_tol=0.010000001)
        except (ValueError, TypeError):
            return False
    return isinstance(actual, str) and " ".join(actual.split()).casefold() == " ".join(expected.split()).casefold()


def load_cases(manifest_path):
    manifest_path = Path(manifest_path).resolve()
    cases = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(cases, list) or not cases:
        raise ValueError("Manifest must contain a nonempty list of cases.")
    seen = set()
    for case in cases:
        if not isinstance(case, dict) or not isinstance(case.get("id"), str) or not case["id"].strip():
            raise ValueError("Each case needs a nonempty string id.")
        if case["id"] in seen:
            raise ValueError("Case ids must be unique.")
        seen.add(case["id"])
        if not isinstance(case.get("file"), str):
            raise ValueError("Each case needs a text file.")
        path = (manifest_path.parent / case["file"]).resolve()
        if not path.is_relative_to(manifest_path.parent) or path.suffix != ".txt" or not path.is_file():
            raise ValueError("Case files must be existing .txt files inside the manifest directory.")
        expected = case.get("expected")
        if not isinstance(expected, dict) or set(expected) != FIELDS:
            raise ValueError("Each case must label all eight benchmark fields.")
        for value in expected.values():
            if value is not None and (isinstance(value, bool) or not isinstance(value, (str, int, float))):
                raise ValueError("Labels must be text, finite numbers, or null.")
            if isinstance(value, (int, float)) and not math.isfinite(value):
                raise ValueError("Labels must be finite.")
    return cases


def isolated_settings(root):
    """Construct settings without loading .env, credentials, or application data."""
    for name in ("uploads", "outputs", "review_exports"):
        (root / name).mkdir(parents=True)
    return Settings(
        app_env="benchmark", data_dir=root, upload_dir=root / "uploads",
        output_dir=root / "outputs", database_path=root / "document_results.db",
        template_store_path=root / "learned_templates.json",
        promoted_template_store_path=root / "promoted_templates.json",
        bad_patterns_path=root / "bad_patterns.json",
        review_export_dir=root / "review_exports", enable_template_learning=False,
        min_learning_pass_ratio=0.6, llm_provider="openai", llm_base_url=None,
        openai_api_key=None, openai_model="unused-in-local-benchmark",
    )


def run_benchmark(manifest_path=DEFAULT_MANIFEST, mode="rule-based", repeats=3):
    if mode not in MODES:
        raise ValueError("Only local extraction modes are supported.")
    if isinstance(repeats, bool) or not isinstance(repeats, int) or not 1 <= repeats <= 20:
        raise ValueError("Repeats must be an integer between 1 and 20.")
    manifest_path = Path(manifest_path).resolve()
    cases = load_cases(manifest_path)
    rows = []
    corpus_hash = hashlib.sha256(manifest_path.read_bytes())
    for case in cases:
        payload = (manifest_path.parent / case["file"]).read_bytes()
        corpus_hash.update(payload)
        runs = []
        for _ in range(repeats):
            with tempfile.TemporaryDirectory(prefix="aiocr-benchmark-") as directory:
                pipeline = DocumentPipeline(isolated_settings(Path(directory)))
                start = perf_counter()
                result = pipeline.process_bytes(Path(case["file"]).name, payload, mode, learn_from_upload=False)
                elapsed_ms = (perf_counter() - start) * 1000
                checks = {field: {
                    "expected": expected, "actual": result.extracted_data.get(field),
                    "match": not result.errors and values_match(result.extracted_data.get(field), expected),
                } for field, expected in case["expected"].items()}
                runs.append({"elapsed_ms": round(elapsed_ms, 3), "fields": checks,
                             "errors": result.errors, "needs_review": result.needs_review,
                             "validation_failures": [check for check in result.validation_results if check["status"] == "fail"]})
        rows.append({"id": case["id"], "file": case["file"], "runs": runs})
    checks = [check for row in rows for run in row["runs"] for check in run["fields"].values()]
    present = [check for check in checks if check["expected"] is not None]
    absent = [check for check in checks if check["expected"] is None]
    times = [run["elapsed_ms"] for row in rows for run in row["runs"]]
    def rate(items):
        return round(sum(item["match"] for item in items) / len(items), 4) if items else None
    return {
        "schema_version": 1, "generated_at": datetime.now(timezone.utc).isoformat(),
        "python": platform.python_version(), "platform": platform.platform(),
        "mode": mode, "repeats": repeats, "documents": len(rows),
        "corpus_sha256": corpus_hash.hexdigest(),
        "method": "Eight scalar fields; fresh store per document per repeat; template learning disabled; no LLM/OCR.",
        "summary": {"matched_fields": sum(check["match"] for check in checks),
                    "evaluated_fields": len(checks), "field_match_rate": rate(checks),
                    "present_field_match_rate": rate(present), "absent_field_match_rate": rate(absent),
                    "pipeline_error_runs": sum(bool(run["errors"]) for row in rows for run in row["runs"]),
                    "median_pipeline_ms": round(statistics.median(times), 3)},
        "cases": rows,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--mode", choices=MODES, default="rule-based")
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        report = run_benchmark(args.manifest, args.mode, args.repeats)
    except (ValueError, OSError) as exc:
        parser.error(str(exc))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps(report["summary"], indent=2))
    return 1 if report["summary"]["pipeline_error_runs"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
