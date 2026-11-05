# Validation record

Local validation on November 5, 2026, with Python 3.12.14:

| Check | Result |
|---|---|
| Benchmark, pipeline, and configuration tests | 345 passed, 55 skipped, 44 expected failures |
| Metrics dashboard data tests | 18 passed |
| Seven-invoice benchmark, both modes, three repeats | Completed with zero pipeline errors |
| Python syntax checks for the new runner and tests | Passed |

Commands used for the test subsets:

```bash
python -m pytest tests/test_benchmark.py tests/test_pipeline.py tests/test_config.py -q
python -m pytest tests/test_metrics_dashboard.py -q
```

Tests used pytest 9.2.0, python-dotenv 1.2.4, and pandas 2.2.3. Existing upstream tests include skips and expected failures; those results are not counted as passes. Upstream datetime deprecation warnings remain.

The full Streamlit UI suite, browser E2E suite, OCR runtime, and Python 3.11 were not validated locally. No application UI or pipeline behavior was changed by this portfolio extension. GitHub CI and a full application demonstration remain separate checks before merging or describing the application as fully verified.
