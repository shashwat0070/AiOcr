# Reproducible local extraction benchmark

## Scope

Seven fictional invoices, eight labeled scalar fields per invoice, three repeats per mode. The same seven documents are repeated for timing; they are not 21 independent layouts. Modes are `rule-based` and `adaptive-local`, with no template learning, existing template store, OCR, or LLM calls.

Cases cover explicit labels, a first-line vendor, shipping, alternate labels, a missing due date, inconsistent totals, and unfamiliar labels. Expected values were written from the synthetic source text. No customer or employer documents are included.

## Measured results

Local run on November 5, 2026, using Python 3.12.14. Reports record environment information, timestamps, and a corpus SHA-256. Timing is illustrative on this machine and does not represent server throughput.

| Mode | Matched / evaluated fields | All labeled fields | Present fields | Absent fields | Median pipeline ms |
|---|---:|---:|---:|---:|---:|
| rule-based | 147/168 | 87.50% | 85.71% | 100.00% | 13.920 |
| adaptive-local | 150/168 | 89.29% | 87.76% | 100.00% | 8.250 |

[Rule-based raw report](benchmark-results/rule-based.json) · [Adaptive-local raw report](benchmark-results/adaptive-local.json)

Neither mode reported a pipeline error in this run. The unfamiliar-label case retains its misses. The inconsistent-total case extracts the stated total while the business validator flags the arithmetic inconsistency. An extraction match does not imply a valid invoice.

## Method

- Evaluate `vendor_name`, `invoice_number`, `invoice_date`, `due_date`, `subtotal`, `tax`, `shipping_handling`, and `total_amount`.
- Compare amounts with an absolute tolerance of one cent. Text comparisons ignore case and repeated whitespace; dates are compared as written, without semantic normalization.
- Score every labeled field. Missing expected values are labeled null; report their match rate separately so absence does not inflate the present-field score unnoticed.
- For pipeline errors, count every field in that run as a miss, including absent fields.
- Construct fresh temporary application storage for every document and repeat. This avoids duplicate skipping and memory leakage across cases.
- Time `process_bytes()` after pipeline construction, including parsing, extraction, validation, and storage. Constructor/database setup, startup, UI, network, and OCR are excluded.
- Report raw per-field expected/actual values, match status, errors, validation failures, and per-run timing.

## Reproduce

From the repository root after installing `requirements-test.txt`:

```bash
python scripts/benchmark_extraction.py --mode rule-based --repeats 3 --output benchmark-results/rule-based.json
python scripts/benchmark_extraction.py --mode adaptive-local --repeats 3 --output benchmark-results/adaptive-local.json
python -m pytest tests/test_benchmark.py -v
```

The script rejects LLM modes and accepts 1-20 repeats. It exits nonzero for invalid inputs or pipeline errors. Field mismatches remain in the report and do not alone cause a nonzero exit, because challenge cases are intentional.

## Limits

This is a small demonstration corpus, not a representative or held-out accuracy study. It does not evaluate PDFs, scanned-image OCR, line items, non-invoice types, calibrated confidence, LLM quality/cost, template training, or human-review effectiveness. Do not substitute these figures for workplace impact metrics.
