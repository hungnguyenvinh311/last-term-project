# Tests

- `unit/`: application unit and regression tests.
- `integration/`: isolated MySQL integration tests; enabled with `RUN_MYSQL_TESTS=1`.
- Root `test_*.py`: catalogue pipeline tests.
- `smoke/`: explicit real-model and browser smoke scripts; these are not run automatically by pytest.
- `experiments/`: explicit detector-quality comparisons and diagnostic runs, with results saved under `data/detector_comparison/`.
- `artifacts/`: pytest temporary files, cache and preserved legacy test directories. Do not use as source code.

Run from the project root: `.venv\Scripts\python.exe -m pytest`.
Real-model checks use `.venv-ai\Scripts\python.exe tests/smoke/ai_smoke.py` or `tests/smoke/ai_api_smoke.py`.
Browser checks use `.venv\Scripts\python.exe tests/smoke/browser_smoke.py`.
Recorded evaluation results remain in `data/test_runs/` and the named experiment directories under `data/`.
