from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.schemas.user_scema import UserCreate, User, UserUpdateUsername, UserUpdatePassword
from app.services import user_service
from app.core.database import get_db

router = APIRouter(tags=["user"])

@router.post("/management-user/create", response_model=User)
def create_user(user: UserCreate, db: Session = Depends(get_db)):
    return user_service.create_user(user=user, db=db)

@router.get("/management-user/get/{id}", response_model=User)
def get_user_by_id(id: int, db: Session = Depends(get_db)):
    return user_service.get_user_by_id(id=id, db=db)

@router.get("/management-user/get-all", response_model=list[User])
def get_all_user(db: Session = Depends(get_db), q: str | None = Query(None, description="Cari berdasarkan nama"),
    page: int = Query(0, description="Nomor halaman"),
    size: int = Query(10, description="Jumlah data per halaman")):
    return user_service.get_all_user(db=db, q=q, page=page, size=size)

@router.post("/management-user/update/{id}", response_model=User)
def update_user(id: int, user: UserUpdateUsername, db: Session = Depends(get_db)):
    return user_service.update_username(id=id, user=user, db=db)

@router.post("/management-user/update-password/{id}", response_model=User)
def update_user_password(id: int, user: UserUpdatePassword, db: Session = Depends(get_db)):
    return user_service.update_user_password(id=id, user=user, db=db)

@router.post("/management-user/delete/{id}")
def delete_user_by_id(id: int, db: Session = Depends(get_db)):
    return user_service.delete_user_by_id(id=id, db=db)

