"""Read-only, authenticated EXP leaderboard for student accounts."""
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from app.api.auth import UserInfo, get_current_user
from app.core.levels import calculate_progress
from app.db.connection import DatabaseNotConfigured, get_engine
router = APIRouter(prefix='/leaderboard', tags=['leaderboard'])
LEADERBOARD_LIMIT = 10
class LeaderboardEntry(BaseModel):
    rank: int
    user_id: int
    username: str
    total_points: int
    current_level: int
    submissions_recorded: int

class LeaderboardResponse(BaseModel):
    total_students: int
    leaders: list[LeaderboardEntry]
    your_rank: int | None
    your_total_points: int | None

def load_leaderboard(user_id: int, role: str) -> tuple[int, list[dict], int | None, int | None]:
    """Rank only students, including accounts without a progress row.

    Equal EXP totals share a rank (e.g. 1, 1, 3). Only usernames,
    scores and counts are shared; emails and passwords are never queried.
    """
    with get_engine().connect() as connection:
        total = connection.execute(text("SELECT COUNT(*) FROM users WHERE role = 'student'")).scalar_one()
        rows = connection.execute(text('SELECT u.user_id, u.username, COALESCE(p.total_points, 0) AS total_points, '
                '  (SELECT COUNT(*) FROM submissions s WHERE s.user_id = u.user_id) AS submissions_recorded '
                'FROM users u ' 'LEFT JOIN user_progress p ON p.user_id = u.user_id ' "WHERE u.role = 'student' "
                'ORDER BY total_points DESC, u.user_id ASC ' 'LIMIT :limit'), {'limit': LEADERBOARD_LIMIT}).mappings().all()
# Administrators can view rankings but don't hold a student rank.
        if role != 'student':
            return int(total), [dict(row) for row in rows], None, None
        own = connection.execute(text('SELECT COALESCE(p.total_points, 0) AS total_points ' 'FROM users u '
                'LEFT JOIN user_progress p ON p.user_id = u.user_id '
                "WHERE u.user_id = :user_id AND u.role = 'student'"), {'user_id': user_id}).mappings().first()
        if own is None:
            return int(total), [dict(row) for row in rows], None, None
        own_points = int(own['total_points'])
        higher = connection.execute(text('SELECT COUNT(*) FROM users u '
                'LEFT JOIN user_progress p ON p.user_id = u.user_id ' "WHERE u.role = 'student' "
                'AND COALESCE(p.total_points, 0) > :total_points'), {'total_points': own_points}).scalar_one()
    return int(total), [dict(row) for row in rows], int(higher) + 1, own_points

@router.get('', response_model=LeaderboardResponse)
def get_leaderboard(user: UserInfo = Depends(get_current_user)) -> LeaderboardResponse:
    try:
        total, rows, your_rank, your_total_points = load_leaderboard(user.user_id, user.role)
    except (DatabaseNotConfigured, SQLAlchemyError):
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail='Database is not available')
    leaders = []
    previous_points: int | None = None
    rank = 0
    for position, row in enumerate(rows, start=1):
        points = int(row['total_points'])
        if previous_points is None or points != previous_points:
            rank = position
        leaders.append(LeaderboardEntry(rank=rank, user_id=int(row['user_id']), username=row['username'],
            total_points=points, current_level=calculate_progress(points)['current_level'],
            submissions_recorded=int(row['submissions_recorded'])))
        previous_points = points
    return LeaderboardResponse(total_students=total, leaders=leaders, your_rank=your_rank,
        your_total_points=your_total_points)
