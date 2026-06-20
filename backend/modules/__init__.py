"""
Domain modules (revamp per PROJECT_PLAN.md §4).

Each module is a self-contained vertical slice:
    router.py   — FastAPI endpoints
    service.py  — business logic / data fetching
    schemas.py  — Pydantic request/response models
    models.py   — SQLAlchemy tables (optional, registered on Base.metadata)
"""
