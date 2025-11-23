from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.schemas.user_scema import UserCreate, User
from app.services import auth_service
from app.core.database import get_db

router = APIRouter(tags=["auth"])

@router.post("/register", response_model=User)
def register(user: UserCreate, db: Session = Depends(get_db)):
    return auth_service.register(db = db, user=user)


@router.post("/login")
def login(form: UserCreate, db: Session = Depends(get_db)):
    return auth_service.login(db = db, form=form)
