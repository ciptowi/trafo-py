from fastapi import Query, Depends, APIRouter
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.group_trafo_scema import GroupTrafoCreate, GroupTrafoCombobox, GroupTrafo
from app.services import group_trafo_service

router = APIRouter(tags=["group trafo"])

@router.post("/group-trafo/save", response_model=GroupTrafo)
def create_group_trafo(group_trafo: GroupTrafoCreate, db: Session = Depends(get_db)):
    return group_trafo_service.create_group_trafo(group_trafo=group_trafo, db=db)

@router.get("/group-trafo/find-all", response_model=list[GroupTrafo])
def read_all_trafo_group(q: str | None = Query(None, description="Cari berdasarkan nama"),
    page: int = 0,
    size: int = 10,
    db: Session = Depends(get_db),
):
    return group_trafo_service.read_all_trafo_group(db=db, q=q, page=page, size=size)

@router.post("/group-trafo/update/{id}", response_model=GroupTrafo)
def update_group_trafo(id: int, group_trafo: GroupTrafoCreate, db: Session = Depends(get_db)):
    return group_trafo_service.update_group_trafo(id=id, group_trafo=group_trafo, db=db)

@router.post("/group-trafo/delete/{id}")
def delete_group_trafo_by_id(id: int, db: Session = Depends(get_db)):
    return group_trafo_service.delete_group_trafo_by_id(id=id, db=db)

@router.get("/group-trafo/combobox", response_model=list[GroupTrafoCombobox])
def read_trafo_group_combobox(db: Session = Depends(get_db)):
    return group_trafo_service.read_trafo_group_combobox(db=db)