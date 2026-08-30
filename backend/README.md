# MaintenAI Backend

FastAPI backend for the MaintenAI predictive maintenance platform.

## Setup

```bash
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

## Run locally

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## API docs

- Swagger UI: http://localhost:8000/docs
- Redoc: http://localhost:8000/redoc
