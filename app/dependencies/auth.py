from fastapi import Depends, HTTPException, status
from fastapi.security import APIKeyHeader
from jose import jwt, JWTError
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from app.core.database import get_db
from app.models.user_model import User

SECRET_KEY = "secret-jwt-key"  # ganti dengan key aman di env
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE = 1440 # in minutes (1 day)

api_key_header = APIKeyHeader(name="Authorization", auto_error=True)

def get_current_user(
    token: str = Depends(api_key_header),
    db: Session = Depends(get_db),
):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid authentication credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = (
        db.query(User)
        .filter(User.username == username)
        .first()
    )

    if user is None:
        raise credentials_exception

    return user


def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)