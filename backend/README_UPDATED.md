# Visionary OCR API (FastAPI)

## Run locally

```bash
# from project root (where ocr-engine/ and backend/ live)
python -m venv .venv && source .venv/bin/activate
pip install -r ocr-engine/requirements.txt
pip install -r backend/requirements.txt
uvicorn backend.app.main:app --reload --port 8000
```

API docs: http://localhost:8000/v1/docs

## Docker

```bash
docker build -t visionary-ocr-api .
docker run --rm -p 8000:8000 visionary-ocr-api

```

## Env

- API_KEY (optional) — if set, clients must send x-api-key: <key>
- CORS_ORIGINS — comma-separated list
- OCR_MODELS, CORRECTION_MODELS (override with env if you want)