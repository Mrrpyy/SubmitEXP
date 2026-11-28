from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from app.api.auth import UserInfo
from app.api.roles import require_student
from app.db.connection import DatabaseNotConfigured, get_engine

# doing student submit history
router = APIRouter(prefix="/history", tags=["history"])

# one row in a studetns own history


class HistoryRow(BaseModel):
    submission_id: int
    assignment_title: str
    course_name: str | None
    submission_type: str
    due_at: datetime | None
    submitted_at: datetime | None
    points_awarded: int | None


class HistoryPage(BaseModel):
    total: int
    limit: int
    offset: int
    submissions: list[HistoryRow]


# database
# one page of of submissions, im putting newest first

def load_history(user_id: int, limit: int, offset: int) -> tuple[int, list[dict]]:
    with get_engine().connect() as connection:
        total = connection.execute(
            text('SELECT COUNT(*) FROM submissions WHERE user_id = :user_id'),
            {'user_id': user_id}
        ).scalar_one()
        rows = connection.execute(
            text(
                'SELECT s.submission_id, s.assignment_title, s.course_name, s.submission_type, '
                '  s.due_at, s.submitted_at, t.points_awarded '
                'FROM submissions s '
                'LEFT JOIN point_transactions t ON t.submission_id = s.submission_id '
                'WHERE s.user_id = :user_id '
                'ORDER BY s.submitted_at DESC, s.submission_id DESC '
                'LIMIT :limit OFFSET :offset'
            ),
            {'user_id': user_id, 'limit': limit, 'offset': offset},
        ).mappings().all()
    return int(total), [dict(row) for row in rows]

# end point
# only students see their own


@router.get('', response_model=HistoryPage)
def my_history(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    user: UserInfo = Depends(require_student),
) -> HistoryPage:
    try:
        total, rows = load_history(user.user_id, limit, offset)
    except (DatabaseNotConfigured, SQLAlchemyError) as err:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail='Database is not available',
        ) from err
    return HistoryPage(
        total=total,
        limit=limit,
        offset=offset,
        submissions=[HistoryRow(**row) for row in rows],
    )
