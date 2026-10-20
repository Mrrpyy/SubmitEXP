import jwt
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, EmailStr, Field, field_validator
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.core.passwords import hash_password, verify_password
from app.core.tokens import TokensNotConfigured, create_access_token, read_user_id
from app.db.connection import DatabaseNotConfigured, get_engine

# user registration (backlog item 2) and login (backlog item 3)
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

# what the extension sends when someone logs in, they can type their username or their email
class LoginRequest(BaseModel):
    identifier: str = Field(min_length=1, max_length=255)
    password: str = Field(min_length=1)
    
# the account details the extension is allowed to see, never the password hash
class UserInfo(BaseModel):
    user_id: int
    username: str
    email: str
    role: str
    
class LoginResponse(BaseModel):
    access_token: str
    token_type: str = 'bearer'
    user: UserInfo
    
# finds the account by username or email it is none if there is no account tha exists
def find_user_for_login(identifier: str) -> dict | None:
    query = text(
        'SELECT user_id, username, email, password_hash, role FROM users '
        'WHERE username = :identifier OR email = :email LIMIT 1'
    )
    with get_engine().connect() as connection:
        row = connection.execute(
            query, {'identifier': identifier, 'email': identifier.lower()}
        ).mappings().first()
    return dict(row) if row else None

# finds the account a token belongs to it is none if it was deleted
def find_user_by_id(user_id: int) -> dict | None:
    query = text('SELECT user_id, username, email, role FROM users WHERE user_id = :user_id')
    with get_engine().connect() as connection:
        row = connection.execute(query, {'user_id': user_id}).mappings().first()
    return dict(row) if row else None

def password_matches(password: str, password_hash: str) -> bool:
    
    if len(password.encode('utf-8')) > 72:
        return False
    return verify_password(password, password_hash)

def user_info(row: dict) -> UserInfo:
    return UserInfo(user_id=row['user_id'], username=row['username'], email=row['email'], role=row['role'])

@router.post('/login', response_model=LoginResponse)
def login(body: LoginRequest) -> LoginResponse:
    try:
        user = find_user_for_login(body.identifier.strip())
    except (DatabaseNotConfigured, SQLAlchemyError):
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail='Database is not available')
    # same message for a wrong password and an unknown account so nobody can use login to find out who has an account
    if user is None or not password_matches(body.password, user['password_hash']):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Incorrect username or password')
    try:
        token = create_access_token(user['user_id'], user['role'])
    except TokensNotConfigured:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail='Login is not set up on the server')
    return LoginResponse(access_token=token, user=user_info(user))

bearer = HTTPBearer(auto_error=False)

def not_logged_in(detail: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED, detail=detail, headers={'WWW-Authenticate': 'Bearer'}
    )
    
# any endpoint that needs a logged in user adds this: user: UserInfo = Depends(get_current_user)
def get_current_user(credentials: HTTPAuthorizationCredentials | None = Depends(bearer)) -> UserInfo:
    if credentials is None:
        raise not_logged_in('Not logged in')
    try:
        user_id = read_user_id(credentials.credentials)
    except TokensNotConfigured:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail='Login is not set up on the server')
    except jwt.InvalidTokenError:
        raise not_logged_in('Login expired, please sign in again')
    try:
        user = find_user_by_id(user_id)
    except (DatabaseNotConfigured, SQLAlchemyError):
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail='Database is not available')
    if user is None:
        raise not_logged_in('Login expired, please sign in again')
    return user_info(user)


# the extension calls this when the popup opens to check the saved login still works
@router.get('/me', response_model=UserInfo)
def me(user: UserInfo = Depends(get_current_user)) -> UserInfo:
    return user