from fastapi import Query, Depends, HTTPException, APIRouter
from sqlalchemy.orm import Session
from database import engine, SessionLocal
from auth import get_current_user
from response import response_ok, response_paginate

import math
import models, schemas

router = APIRouter(tags=["group trafo"])

# Dependency DB
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Create table 'group trafo' when not exist
models.Base.metadata.create_all(bind=engine, tables=[models.GroupTrafo.__table__])

# CREATE GROUP TRAFO
@router.post("/group-trafo/save", response_model=schemas.GroupTrafo)
def create_group_trafo(group_trafo: schemas.GroupTrafoCreate, db: Session = Depends(get_db)):
    new_group_trafo = models.GroupTrafo(**group_trafo.dict())
    db.add(new_group_trafo)
    db.commit()
    db.refresh(new_group_trafo)
    return response_ok(data=None, message="Group Trafo created")

# READ ALL
@router.get("/group-trafo/find-all", response_model=list[schemas.GroupTrafo])
def read_all_trafo_group(q: str | None = Query(None, description="Cari berdasarkan nama"),
    page: int = 0,
    size: int = 10,
    db: Session = Depends(get_db),
):
    base_query = db.query(models.GroupTrafo)
    if q:
        base_query = base_query.filter(models.GroupTrafo.name.contains(q))
    total = base_query.count()
    totalPage = math.ceil(total / size) if total > 0 else 0
    list_of_trafo_group_models = base_query.offset(page * size).limit(size).all()
    data_for_response = [schemas.GroupTrafo.model_validate(group).model_dump() for group in list_of_trafo_group_models]    
    return response_paginate(data_for_response, page, size, total, totalPage)

# UPDATE GROUP TRAFO BY ID
@router.post("/group-trafo/update/{id}", response_model=schemas.GroupTrafo)
def update_group_trafo(id: int, group_trafo: schemas.GroupTrafoCreate, db: Session = Depends(get_db)):
    db_group_trafo = db.query(models.GroupTrafo).filter(models.GroupTrafo.id == id).first()
    if not db_group_trafo:
        raise HTTPException(status_code=404, detail="Group Trafo not found")
    for key, value in group_trafo.dict().items():
        setattr(db_group_trafo, key, value)
    db.commit()
    db.refresh(db_group_trafo)
    return response_ok(data=None, message="Group Trafo updated")

# DELETE GROUP TRAFO BY ID
@router.post("/group-trafo/delete/{id}")
def delete_group_trafo_by_id(id: int, db: Session = Depends(get_db)):
    db_group_trafo = db.query(models.GroupTrafo).filter(models.GroupTrafo.id == id).first()
    if not db_group_trafo:
        raise HTTPException(status_code=404, detail="Group Trafo not found")
    db.delete(db_group_trafo)
    db.commit()
    return response_ok(data=None, message=f"Group Trafo {id} deleted")

# READ ALL
@router.get("/group-trafo/combobox", response_model=list[schemas.Combobox])
def read_trafo_group_combobox(db: Session = Depends(get_db)):
    groups = db.query(models.GroupTrafo).all()
    combobox = [schemas.Combobox(id=group.id, name=group.name).model_dump() for group in groups]
    return response_ok(data=combobox)