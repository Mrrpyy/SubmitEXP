from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.api.auth import UserInfo, get_current_user
from app.api.roles import STUDENT
from app.core.levels import calculate_progress
from app.db.connection import DatabaseNotConfigured, get_engine

# user profile and dashboard (backlog item 15)
router = APIRouter(prefix='/profile', tags=['profile'])


# ---------- response shapes ----------

# numbers for the dashboard, students only since admins do not earn exp
class ProfileStats(BaseModel):
    total_points: int
    current_level: int
    exp_in_level: int
    exp_for_next_level: int
    exp_to_next_level: int
    progress_percent: int
    submissions_recorded: int
    early_submissions: int
    best_award: int
    average_award: int
    last_submitted_at: datetime | None


class ProfileResponse(BaseModel):
    user_id: int
    username: str
    email: str
    role: str
    member_since: datetime | None
    stats: ProfileStats | None


# ---------- database ----------

def load_member_since(user_id: int) -> datetime | None:
    query = text('SELECT created_at FROM users WHERE user_id = :user_id')
    with get_engine().connect() as connection:
        row = connection.execute(query, {'user_id': user_id}).mappings().first()
    return row['created_at'] if row else None


# one query for every dashboard number
def load_stats(user_id: int) -> dict:
    query = text(
        'SELECT '
        '  COALESCE((SELECT total_points FROM user_progress WHERE user_id = :user_id), 0) AS total_points, '
        '  COUNT(s.submission_id) AS submissions_recorded, '
        '  COALESCE(SUM(s.submitted_at < s.due_at), 0) AS early_submissions, '
        '  COALESCE(MAX(t.points_awarded), 0) AS best_award, '
        '  COALESCE(ROUND(AVG(t.points_awarded)), 0) AS average_award, '
        '  MAX(s.submitted_at) AS last_submitted_at '
        'FROM submissions s '
        'LEFT JOIN point_transactions t ON t.submission_id = s.submission_id '
        'WHERE s.user_id = :user_id'
    )
    with get_engine().connect() as connection:
        row = connection.execute(query, {'user_id': user_id}).mappings().first()
    return dict(row) if row else {}


# ---------- building the response ----------

# turns raw database numbers into the stats the extension shows
def build_stats(row: dict) -> ProfileStats:
    # mysql can hand back decimals and none, so force everything to int
    total_points = int(row.get('total_points') or 0)
    return ProfileStats(
        total_points=total_points,
        submissions_recorded=int(row.get('submissions_recorded') or 0),
        early_submissions=int(row.get('early_submissions') or 0),
        best_award=int(row.get('best_award') or 0),
        average_award=int(row.get('average_award') or 0),
        last_submitted_at=row.get('last_submitted_at'),
        **calculate_progress(total_points),
    )


# ---------- endpoint ----------

# any logged in user sees their own profile, only students get stats
@router.get('', response_model=ProfileResponse)
def my_profile(user: UserInfo = Depends(get_current_user)) -> ProfileResponse:
    try:
        member_since = load_member_since(user.user_id)
        stats = build_stats(load_stats(user.user_id)) if user.role == STUDENT else None
    except (DatabaseNotConfigured, SQLAlchemyError):
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail='Database is not available')
    return ProfileResponse(
        user_id=user.user_id,
        username=user.username,
        email=user.email,
        role=user.role,
        member_since=member_since,
        stats=stats,
    )