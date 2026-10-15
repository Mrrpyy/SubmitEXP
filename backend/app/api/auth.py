from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, EmailStr, Field, field_validator
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.core.passwords import hash_password
from app.db.connection import get_engine

# user registration, backlog item 2
router = APIRouter(prefix='/auth', tags=['auth'])


# what the extension sends when someone signs up
class RegisterRequest(BaseModel):
    # letters, numbers and underscores only, 3 to 50 characters to match the database
    username: str = Field(min_length=3, max_length=50, pattern=r'^[A-Za-z0-9_]+$')
    email: EmailStr
    password: str = Field(min_length=8)

    @field_validator('password')
    @classmethod
    def password_not_too_long(cls, value: str) -> str:
        # bcrypt only reads the first 72 bytes, anything longer would get cut off without warning
        if len(value.encode('utf-8')) > 72:
            raise ValueError('Password must be 72 bytes or fewer')
        return value

    @field_validator('email')
    @classmethod
    def lowercase_email(cls, value: str) -> str:
        # same email in different capitals counts as one account
        return value.lower()


# what we send back, no password or hash ever leaves the server
class RegisterResponse(BaseModel):
    user_id: int
    username: str
    email: str
    role: str


# returns username or email if one is already taken, otherwise None
def find_taken_field(username: str, email: str) -> str | None:
    query = text(
        'SELECT username, email FROM users WHERE username = :username OR email = :email LIMIT 1'
    )
    with get_engine().connect() as connection:
        row = connection.execute(query, {'username': username, 'email': email}).mappings().first()
    if row is None:
        return None
    # database ignores capital letters, so compare in lowercase too
    return 'username' if row['username'].lower() == username.lower() else 'email'


# saves the user and their starting progress row together
def insert_user(username: str, email: str, password_hash: str) -> int:
    # begin means both inserts succeed or both get undone, no half made accounts
    with get_engine().begin() as connection:
        result = connection.execute(
            text(
                "INSERT INTO users (username, email, password_hash, role) "
                "VALUES (:username, :email, :password_hash, 'student')"
            ),
            {'username': username, 'email': email, 'password_hash': password_hash},
        )
        user_id = int(result.lastrowid)
        connection.execute(
            text('INSERT INTO user_progress (user_id) VALUES (:user_id)'),
            {'user_id': user_id},
        )
    return user_id


# every new account is a student, nobody can sign up as admin
@router.post('/register', status_code=status.HTTP_201_CREATED, response_model=RegisterResponse)
def register(body: RegisterRequest) -> RegisterResponse:
    taken = find_taken_field(body.username, body.email)
    if taken:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f'That {taken} is already in use')
    try:
        user_id = insert_user(body.username, body.email, hash_password(body.password))
    except IntegrityError:
        # two sign ups with the same name at the same moment, the database unique rule catches the second
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail='That username or email is already in use')
    return RegisterResponse(user_id=user_id, username=body.username, email=body.email, role='student')