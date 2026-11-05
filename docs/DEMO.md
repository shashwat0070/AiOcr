# Five-minute demo

Use the fictional text examples so the demo requires no model API key or OCR installation.

## Start

Install `requirements-test.txt`, then run `python -m streamlit run app.py` from the repository root. Select **rule-based** extraction. Use an empty local data directory if the same files were already uploaded; duplicate detection intentionally prevents repeat processing.

## Walkthrough

1. Upload `examples/benchmark/standard.txt` in the single-document tab. Compare extracted fields to source text. Show validation and export controls.
2. Upload `examples/benchmark/inconsistent-total.txt`. Its subtotal is 1,000, tax 80, and total 999. Faithfully extracting 999 is different from approving the invoice: the total-consistency rule should fail.
3. Upload `examples/benchmark/unfamiliar-labels.txt`. Show missed fields and the correction form. Do not describe correction as model fine-tuning.
4. Run both benchmark commands from the README. Show expected/extracted field values, match status, validation failures, and timing in the JSON reports.

## Suggested narration

"This was a team capstone, and I contributed across architecture, extraction, validation, storage, interface work, testing, and documentation. The prototype turns documents into reviewable records. My portfolio extension adds a small labeled benchmark so readers can reproduce both successful extraction and limitations."

## Recording

Capture an upload, extracted fields, a validation failure, a manual correction, and an export. Use synthetic inputs with no credentials visible. Screenshots should show a running instance rather than a mockup.
