# PDF Knowledge Hub Backend

FastAPI backend scaffold for the PDF Knowledge Hub MVP.

## Local setup

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -e ".[dev]"
copy .env.example .env
uvicorn app.main:app --reload
```

API docs:

```text
http://localhost:8000/docs
```

Health check:

```text
GET /health
```

