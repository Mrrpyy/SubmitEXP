from datetime import datetime, timedelta, timezone

import jwt

from app.core import config

#how long the login lasts
TOKEN_LIFETIME = timedelta(days=7)

class TokensNotConfigured(RuntimeError):
    pass

# server starts ithout a secret, it is read when the function is called
def get_secret() -> str:
    if not config.JWT_SECRET:
        raise TokensNotConfigured('JWT_SECRET missing from .env')
    return config.JWT_SECRET

# creates a signed token with the user id and role
def create_access_token(user_id: int, role: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {'sub': str(user_id), 'role': role, 'iat': now, 'exp': now + TOKEN_LIFETIME}
    return jwt.encode(payload, get_secret(), algorithm='HS256')

# gives back the user id from a good token, if it isnt good it raises an error
def read_user_id(token: str) -> int:
    payload = jwt.decode(token, get_secret(), algorithms=['HS256'], options={'require': ['exp', 'sub']})
    try:
        return int(payload['sub'])
    except ValueError as exc:
        raise jwt.InvalidTokenError('Bad user id in token') from exc