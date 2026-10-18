from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.api.router import api_router
from app.db.connection import DatabaseNotConfigured, get_engine

app = FastAPI(title="SubmitEXP API", version="0.1.0")

# Allow the Vite dev preview and locally installed Chrome extensions.
# In production, replace the regex with the single approved extension ID.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_origin_regex=r"^chrome-extension://[a-p]{32}$",
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "Authorization"],
)

app.include_router(api_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/health/database")
def database_health() -> dict[str, str]:
    try:
        with get_engine().connect() as connection:
            connection.execute(text("SELECT 1"))
    except DatabaseNotConfigured as exc:
        raise HTTPException(status_code=503, detail="Database is not configured") from exc
    except SQLAlchemyError as exc:
        # Never expose credentials in error responses.
        raise HTTPException(status_code=503, detail="Database connection failed") from exc

    return {"status": "ok", "database": "reachable"}
