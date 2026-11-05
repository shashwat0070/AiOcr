"""Benchmark scoring, corpus integrity, and repeat isolation."""
import json
import pytest

from scripts.benchmark_extraction import DEFAULT_MANIFEST, load_cases, run_benchmark, values_match


@pytest.mark.parametrize("actual,expected,match", [
    ("  NORTHSTAR   Supplies ", "Northstar Supplies", True),
    (1080.005, 1080.0, True), (1080.02, 1080.0, False),
    (None, 80.0, False), (None, None, True), ("", None, True),
    (0, None, False), (True, 1.0, False), (float("nan"), 1.0, False),
    ("01/15/2026", "2026-01-15", False),
])
def test_scoring_rules(actual, expected, match):
    assert values_match(actual, expected) is match


@pytest.mark.parametrize("mode", ["rule-based", "adaptive-local"])
def test_repeats_use_fresh_stores_and_preserve_challenge_failures(mode):
    report = run_benchmark(mode=mode, repeats=2)
    assert report["documents"] == 7
    assert report["summary"]["evaluated_fields"] == 7 * 8 * 2
    assert report["summary"]["pipeline_error_runs"] == 0
    assert report["summary"]["field_match_rate"] < 1
    standard = report["cases"][0]["runs"]
    assert all(run["fields"]["invoice_number"]["match"] for run in standard)
    assert all(not run["errors"] for run in standard)
    inconsistent = next(case for case in report["cases"] if case["id"] == "inconsistent-total")
    assert any(check["field"] == "total_consistency" for check in inconsistent["runs"][0]["validation_failures"])
    assert inconsistent["runs"][0]["fields"]["total_amount"]["match"]
    challenge = next(case for case in report["cases"] if case["id"] == "unfamiliar-labels")
    assert not challenge["runs"][0]["fields"]["invoice_number"]["match"]


def test_pipeline_errors_count_every_field_as_missed(monkeypatch):
    from src.doc_ai.pipeline import DocumentPipeline
    original = DocumentPipeline.process_bytes
    def with_error(self, *args, **kwargs):
        result = original(self, *args, **kwargs)
        result.errors.append("Simulated pipeline failure")
        return result
    monkeypatch.setattr(DocumentPipeline, "process_bytes", with_error)
    summary = run_benchmark(repeats=1)["summary"]
    assert summary["pipeline_error_runs"] == 7
    assert summary["field_match_rate"] == 0
    assert summary["absent_field_match_rate"] == 0


@pytest.mark.parametrize("repeats", [0, -1, 21, True, 1.5])
def test_invalid_repeat_counts(repeats):
    with pytest.raises(ValueError, match="Repeats"):
        run_benchmark(repeats=repeats)


def test_rejects_paid_modes():
    with pytest.raises(ValueError, match="local"):
        run_benchmark(mode="llm-assisted")


@pytest.mark.parametrize("mutation", ["empty", "duplicate", "missing-label", "outside", "nan"])
def test_invalid_manifests(tmp_path, mutation):
    cases = json.loads(DEFAULT_MANIFEST.read_text())[:1]
    (tmp_path / cases[0]["file"]).write_bytes((DEFAULT_MANIFEST.parent / cases[0]["file"]).read_bytes())
    if mutation == "empty":
        cases = []
    elif mutation == "duplicate":
        cases += cases
    elif mutation == "missing-label":
        del cases[0]["expected"]["tax"]
    elif mutation == "outside":
        cases[0]["file"] = "../outside.txt"
    elif mutation == "nan":
        cases[0]["expected"]["tax"] = float("nan")
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps(cases))
    with pytest.raises(ValueError):
        load_cases(manifest)
