import bcrypt


# turns a plain password into a bcrypt hash, the real password is never stored
def hash_password(password: str) -> str:
    # gensalt adds random data so two people with the same password get different hashes
    hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
    return hashed.decode('utf-8')


# checks a typed password against a stored hash, login will use this
def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))