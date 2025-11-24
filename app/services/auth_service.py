from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.core.database import Base, engine
from app.dependencies.auth import create_access_token
from app.dependencies.response import response_ok
from app.dependencies.cryptography import verify_password, hash_password
from app.models.user_model import User
from app.schemas.user_scema import UserCreate

# Create table 'user' when not exist
Base.metadata.create_all(bind=engine, tables=[User.__table__])

def register(user: UserCreate, db: Session):
    db_user = db.query(User).filter(User.username == user.username).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Username already registered")
    hashed_pw = hash_password(user.password)
    new_user = User(username=user.username, password=hashed_pw)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

def login(form: UserCreate, db: Session):
    user = db.query(User).filter(User.username == form.username).first()
    if not user or not verify_password(form.password, user.password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    access_token = create_access_token({"sub": user.username})
    return response_ok(data={"access_token": access_token, "token_type": "bearer"})