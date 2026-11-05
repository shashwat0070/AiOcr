# Architecture and design decisions

## Scenario

An analyst receives invoices with different layouts and needs structured records that can be inspected, corrected, and exported. The prototype prioritizes a visible review loop and a locally runnable demonstration.

## Data flow

1. Streamlit receives an upload and extraction mode.
2. The parser reads text, or tries PDF text extraction followed by OCR fallback.
3. The pipeline checks duplicates and routes content through the selected extractor.
4. Rules/templates or optional LLM assistance produce structured fields.
5. Validators check required values, date formats, positive totals, and subtotal/tax/shipping consistency.
6. A reviewer compares fields with the source and corrects them.
7. Storage writes structured results and traces; eligible approved results can update template memory.

## Tradeoffs

| Decision | Benefit | Limitation |
|---|---|---|
| Local rules and templates | Inspectable behavior; local paths have no model call charge | Sensitive to layout and labels |
| Optional LLM fallback | Can help with unfamiliar formats | Provider dependence, variable output, latency, cost |
| Human review | A visible correction path | Reviewer time; confidence alone does not establish correctness |
| SQLite | Portable local demonstration | Does not establish concurrent multi-tenant database behavior |
| Streamlit | Fast technical demo | Production access controls and application design require further work |
| Explicit validation | Missing values and inconsistent totals are visible | Passing rules does not establish agreement with the source |

## Benchmark boundary

The runner calls the real `DocumentPipeline.process_bytes()` path on synthetic text. Each document/repeat gets its own database and empty template store. Learning is disabled. Timing includes parsing, extraction, validation, and persistence after pipeline construction. It excludes constructor/database initialization, startup, UI rendering, OCR, and network calls. This measures cold local extraction, not template retrieval improvements.

## Future AWS direction

A future version could use S3 for documents, queued workers for processing, RDS for shared records, and managed monitoring. Real customer use would require authentication, authorization, retention controls, secret management, and workload-specific evaluation. This branch does not deploy cloud resources.
