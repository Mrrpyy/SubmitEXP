from fastapi import FastAPI, HTTPException
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.api.router import api_router
from app.db.connection import DatabaseNotConfigured, get_engine

app = FastAPI(title='SubmitEXP API', version='0.1.0')

# all route files get plugged in through the router file, so this file stays the same
app.include_router(api_router)


@app.get('/health')
def health() -> dict[str, str]:
    return {'status': 'ok'}


@app.get('/health/database')
def database_health() -> dict[str, str]:
    try:
        with get_engine().connect() as connection:
            connection.execute(text('SELECT 1'))
    except DatabaseNotConfigured as exc:
        raise HTTPException(status_code=503, detail='Database is not configured') from exc
    except SQLAlchemyError as exc:
        # never show the database url or password in a response
        raise HTTPException(status_code=503, detail='Database connection failed') from exc
    return {'status': 'ok', 'database': 'reachable'}