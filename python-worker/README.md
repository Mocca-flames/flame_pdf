Smart PDF Generator (Phase 3)

Quick start

1. Create and activate a Python venv (recommended)

```bash
python -m venv .venv
.\.venv\Scripts\activate
```

2. Install dependencies

```bash
pip install -r requirements.txt
```

3. Run the service locally

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

API

- `POST /generate-pdf` - accepts multipart files (field name `files`) and returns a PDF
- `GET /health` - basic healthcheck

Notes

- This skeleton implements a best-effort processing pipeline using `rembg`, `opencv`, and `Pillow`.
- For production, add proper temp-file cleanup, rate-limiting, and authentication.
