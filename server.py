"""Server entry compatible with Emergent supervisor (uvicorn server:app on :8001).

For local-only execution on port 5812, use run.py.
"""
from app.main import app  # noqa: F401
