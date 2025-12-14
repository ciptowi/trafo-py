from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.dependencies.auth import get_current_user
from app.core.database import get_db
from app.models.user_model import User
from app.schemas.trafo_scema import TrafoCreate, Trafo, TrafoDetail
from app.services import trafo_service

router = APIRouter(tags=["trafo"])

@router.post("/trafo/save")
def create_trafo(
    trafo: TrafoCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return trafo_service.create_trafo(
        trafo=trafo,
        db=db,
        user=current_user
    )



@router.get("/trafo/find-all", response_model=list[Trafo])
def read_all_trafo(q: str | None = Query(None, description="Cari berdasarkan nama"),
    groupId: int = Query(description="ID Group Trafo wajib"),
    page: int = Query(0, description="Nomor halaman"),
    size: int = Query(10, description="Jumlah data per halaman"),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    # note: groupId ambil dari user
    return trafo_service.read_all_trafo(db=db, q=q, groupId=groupId, page=page, size=size, user=current_user)

@router.get("/trafo/find-one/{id}", response_model=TrafoDetail)
def read_trafo(id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    return trafo_service.read_trafo(id=id, db=db, user=current_user)

@router.post("/trafo/update/{id}", response_model=Trafo)
def update_trafo(id: int, trafo: TrafoCreate, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    return trafo_service.update_trafo(id=id, trafo=trafo, db=db, user=current_user)

@router.post("/trafo/delete/{id}")
def delete_trafo_by_id(id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    return trafo_service.delete_trafo_by_id(id=id, db=db, user=current_user)
