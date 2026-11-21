# BrewPass Backend

FastAPI service exposing the BrewPass REST API under `/api/v1`.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

uvicorn app.main:app --reload   # http://localhost:8000/api/v1/docs
pytest                          # run tests
ruff check . && ruff format --check .
```
