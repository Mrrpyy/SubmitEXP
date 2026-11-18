from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.api.auth import UserInfo
from app.api.roles import require_admin
from app.db.connection import DatabaseNotConfigured, get_engine

# endpoints only admins can use, the admin interface (backlog item 18) is built on these
router = APIRouter(prefix='/admin', tags=['admin'])


# ---------- response shapes ----------

# one row in the admin user list, no password hash
class AdminUserRow(BaseModel):
    user_id: int
    username: str
    email: str
    role: str
    total_points: int


class RoleChangeRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')

    # pydantic rejects anything that is not one of these two
    role: Literal['student', 'admin']


# totals for the top of the admin interface
class AdminStats(BaseModel):
    total_users: int
    students: int
    admins: int
    total_submissions: int
    total_points_awarded: int


# one submission in an administrator's read-only history view
class AdminSubmissionRow(BaseModel):
    submission_id: int
    assignment_title: str
    course_name: str | None
    submission_type: str
    due_at: datetime | None
    submitted_at: datetime | None
    created_at: datetime
    canvas_course_id: int | None
    canvas_assignment_id: int | None
    points_awarded: int | None


class AdminSubmissionPage(BaseModel):
    user_id: int
    total: int
    limit: int
    offset: int
    submissions: list[AdminSubmissionRow]


def database_down() -> HTTPException:
    return HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail='Database is not available')


# ---------- database ----------

# every account with its points, newest first
def load_all_users() -> list[dict]:
    query = text(
        'SELECT u.user_id, u.username, u.email, u.role, COALESCE(p.total_points, 0) AS total_points '
        'FROM users u '
        'LEFT JOIN user_progress p ON p.user_id = u.user_id '
        'ORDER BY u.user_id DESC'
    )
    with get_engine().connect() as connection:
        rows = connection.execute(query).mappings().all()
    return [dict(row) for row in rows]


# finds one account, none if it does not exist
def find_user_row(user_id: int) -> dict | None:
    return next((row for row in load_all_users() if row['user_id'] == user_id), None)


def save_role(user_id: int, role: str) -> None:
    with get_engine().begin() as connection:
        connection.execute(
            text('UPDATE users SET role = :role WHERE user_id = :user_id'),
            {'role': role, 'user_id': user_id},
        )


# counts for the whole app in one query
def load_stats() -> dict:
    query = text(
        'SELECT '
        '  (SELECT COUNT(*) FROM users) AS total_users, '
        "  (SELECT COUNT(*) FROM users WHERE role = 'student') AS students, "
        "  (SELECT COUNT(*) FROM users WHERE role = 'admin') AS admins, "
        '  (SELECT COUNT(*) FROM submissions) AS total_submissions, '
        '  (SELECT COALESCE(SUM(points_awarded), 0) FROM point_transactions) AS total_points_awarded'
    )
    with get_engine().connect() as connection:
        row = connection.execute(query).mappings().first()
    return dict(row) if row else {}


# Page through one account's submissions. A missing EXP transaction stays null,
# rather than being reported as a zero-point award.
def load_submission_history(user_id: int, limit: int, offset: int) -> tuple[int, list[dict]] | None:
    with get_engine().connect() as connection:
        # TIMESTAMP (created_at) is returned in UTC; DATETIME values are stored as UTC.
        connection.execute(text("SET time_zone = '+00:00'"))
        found = connection.execute(
            text('SELECT 1 FROM users WHERE user_id = :user_id'),
            {'user_id': user_id},
        ).first()
        if found is None:
            return None

        total = connection.execute(
            text('SELECT COUNT(*) FROM submissions WHERE user_id = :user_id'),
            {'user_id': user_id},
        ).scalar_one()
        rows = connection.execute(
            text(
                'SELECT s.submission_id, s.assignment_title, s.course_name, '
                's.submission_type, s.due_at, s.submitted_at, s.created_at, '
                's.canvas_course_id, s.canvas_assignment_id, t.points_awarded '
                'FROM submissions s '
                'LEFT JOIN point_transactions t ON t.submission_id = s.submission_id '
                'WHERE s.user_id = :user_id '
                'ORDER BY s.submitted_at DESC, s.submission_id DESC '
                'LIMIT :limit OFFSET :offset'
            ),
            {'user_id': user_id, 'limit': limit, 'offset': offset},
        ).mappings().all()
    return int(total), [dict(row) for row in rows]


# ---------- endpoints ----------

@router.get('/users', response_model=list[AdminUserRow])
def list_users(admin: UserInfo = Depends(require_admin)) -> list[AdminUserRow]:
    try:
        rows = load_all_users()
    except (DatabaseNotConfigured, SQLAlchemyError):
        raise database_down()
    return [AdminUserRow(**row) for row in rows]


@router.get('/stats', response_model=AdminStats)
def app_stats(admin: UserInfo = Depends(require_admin)) -> AdminStats:
    try:
        row = load_stats()
    except (DatabaseNotConfigured, SQLAlchemyError):
        raise database_down()
    # mysql sum comes back as a decimal, so force ints
    return AdminStats(**{field: int(row.get(field) or 0) for field in AdminStats.model_fields})


@router.get('/users/{user_id}/submissions', response_model=AdminSubmissionPage)
def user_submissions(
    user_id: int,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    admin: UserInfo = Depends(require_admin),
) -> AdminSubmissionPage:
    try:
        result = load_submission_history(user_id, limit, offset)
    except (DatabaseNotConfigured, SQLAlchemyError):
        raise database_down()
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='User not found')
    total, rows = result
    return AdminSubmissionPage(
        user_id=user_id,
        total=total,
        limit=limit,
        offset=offset,
        submissions=[AdminSubmissionRow(**row) for row in rows],
    )


# post instead of patch because the server only allows get and post from the extension
@router.post('/users/{user_id}/role', response_model=AdminUserRow)
def change_role(user_id: int, body: RoleChangeRequest, admin: UserInfo = Depends(require_admin)) -> AdminUserRow:
    # stops an admin from removing their own access by mistake
    if user_id == admin.user_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='You cannot change your own role')
    try:
        # look first, mysql counts an update to the same role as zero rows changed
        target = find_user_row(user_id)
        if target is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='User not found')
        save_role(user_id, body.role)
    except (DatabaseNotConfigured, SQLAlchemyError):
        raise database_down()
    return AdminUserRow(**{**target, 'role': body.role})