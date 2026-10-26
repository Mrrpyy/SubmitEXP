from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.api.auth import UserInfo
from app.api.roles import require_student
from app.db.connection import DatabaseNotConfigured, get_engine

# endpoints only students can use
router = APIRouter(prefix='/student', tags=['student'])


class StudentProgress(BaseModel):
    username: str
    total_points: int
    current_level: int
    submissions_recorded: int


# reads the progress row and counts the submissions for one student
def load_progress(user_id: int) -> dict:
    query = text(
        'SELECT '
        '  COALESCE(p.total_points, 0) AS total_points, '
        '  COALESCE(p.current_level, 1) AS current_level, '
        '  (SELECT COUNT(*) FROM submissions s WHERE s.user_id = :user_id) AS submissions_recorded '
        'FROM users u '
        'LEFT JOIN user_progress p ON p.user_id = u.user_id '
        'WHERE u.user_id = :user_id'
    )
    with get_engine().connect() as connection:
        row = connection.execute(query, {'user_id': user_id}).mappings().first()
    # a missing row means no progress yet, so start from zero
    if row is None:
        return {'total_points': 0, 'current_level': 1, 'submissions_recorded': 0}
    return dict(row)


# the logged in student sees only their own points and level
@router.get('/progress', response_model=StudentProgress)
def my_progress(user: UserInfo = Depends(require_student)) -> StudentProgress:
    try:
        row = load_progress(user.user_id)
    except (DatabaseNotConfigured, SQLAlchemyError):
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail='Database is not available')
    return StudentProgress(
        username=user.username,
        total_points=int(row['total_points']),
        current_level=int(row['current_level']),
        submissions_recorded=int(row['submissions_recorded']),
    )