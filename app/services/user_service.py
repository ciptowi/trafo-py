import math
from fastapi import HTTPException, Query
from sqlalchemy.orm import Session, joinedload

from app.core.database import Base, engine
from app.dependencies.response import response_ok, response_paginate
from app.dependencies.cryptography import verify_password, hash_password
from app.models.user_model import User
from app.schemas.user_scema import UserCreate, UserUpdatePassword, UserUpdateUsername, UserView

# Create table 'user' when not exist
Base.metadata.create_all(bind=engine, tables=[User.__table__])

def create_user(user: UserCreate, db: Session):
    db_user = db.query(User).filter(User.username == user.username).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Username already registered")
    hashed_pw = hash_password(user.password)
    new_user = User(username=user.username, password=hashed_pw, group_id=user.group_id)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return response_ok(data=None, message="User created")

def get_user_by_id(id: int, db: Session):
    db_user = db.query(User).filter(User.id == id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    user_schema = UserView.model_validate(db_user)
    user_data = user_schema.model_dump()
    return response_ok(data=user_data)

def get_all_user(db: Session, q: str | None = Query(None, description="Cari berdasarkan nama"),
    page: int = Query(0, description="Nomor halaman"),
    size: int = Query(10, description="Jumlah data per halaman"),
):
    base_query = db.query(User).options(joinedload(User.group))
    if q:
        base_query = base_query.filter(User.username.contains(q))
    total = base_query.count()
    totalPage = math.ceil(total / size) if total > 0 else 0
    list_of_user_models = base_query.offset(page * size).limit(size).all()
    data_for_response = [UserView.model_validate(user).model_dump() for user in list_of_user_models]    
    return response_paginate(data_for_response, page, size, total, totalPage)

def update_username(id: int, user: UserUpdateUsername, db: Session):
    db_user = db.query(User).filter(User.id == id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    for key, value in user.dict().items():
        setattr(db_user, key, value)
    db.commit()
    db.refresh(db_user)
    return response_ok(data=None, message="User updated")

def update_user_password(id: int, user: UserUpdatePassword, db: Session):
    db_user = db.query(User).filter(User.id == id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    if not verify_password(user.oldPassword, db_user.password):
        raise HTTPException(status_code=400, detail="Incorrect password")
    for key, value in user.dict().items():
        setattr(db_user, key, value)
    db.commit()
    db.refresh(db_user)
    return response_ok(data=None, message="User updated")

def delete_user_by_id(id: int, db: Session):
    db_user = db.query(User).filter(User.id == id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    db.delete(db_user)
    db.commit()
    return response_ok(data=None, message="User deleted")