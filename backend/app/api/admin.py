from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.api.auth import UserInfo
from app.api.roles import require_admin
from app.db.connection import DatabaseNotConfigured, get_engine

# endpoints only admins can use
router = APIRouter(prefix='/admin', tags=['admin'])


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


def database_down() -> HTTPException:
    return HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail='Database is not available')


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


@router.get('/users', response_model=list[AdminUserRow])
def list_users(admin: UserInfo = Depends(require_admin)) -> list[AdminUserRow]:
    try:
        rows = load_all_users()
    except (DatabaseNotConfigured, SQLAlchemyError):
        raise database_down()
    return [AdminUserRow(**row) for row in rows]


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