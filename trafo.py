from fastapi import APIRouter, Depends, HTTPException, Query
from response import response_ok, response_paginate
from database import SessionLocal, engine
from sqlalchemy.orm import Session, joinedload
from auth import get_current_user

import models, schemas
import math

router = APIRouter(tags=["trafo"])

# Dependency DB
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
        
# Create table 'trafo' when not exist
models.Base.metadata.create_all(bind=engine, tables=[models.Trafo.__table__])

# CREATE
@router.post("/trafo/save", response_model=schemas.Trafo)
def create_trafo(trafo: schemas.TrafoCreate, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    new_trafo = models.Trafo(**trafo.dict(), owner_id=current_user.id)
    db.add(new_trafo)
    db.commit()
    db.refresh(new_trafo)
    return response_ok(data=None, message="Trafo created")

# READ ALL
@router.get("/trafo/find-all", response_model=list[schemas.Trafo])
def read_all_trafo(q: str | None = Query(None, description="Cari berdasarkan nama"),
    groupId: int = Query(description="ID Group Trafo wajib"),
    page: int = Query(0, description="Nomor halaman"),
    size: int = Query(10, description="Jumlah data per halaman"),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    base_query = db.query(models.Trafo).filter(models.Trafo.owner_id == current_user.id, models.Trafo.group_id == groupId)
    if q:
        base_query = base_query.filter(models.Trafo.name.contains(q))
    total = base_query.count()
    totalPage = math.ceil(total / size) if total > 0 else 0
    list_of_trafo_models = base_query.offset(page * size).limit(size).all()
    data_for_response = [schemas.Trafo.model_validate(trafo).model_dump() for trafo in list_of_trafo_models]    
    return response_paginate(data_for_response, page, size, total, totalPage)

# READ BY ID
@router.get("/trafo/find-one/{id}", response_model=schemas.TrafoDetail)
def read_trafo(id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    trafo = db.query(models.Trafo).options(joinedload(models.Trafo.group)).filter(models.Trafo.id == id, models.Trafo.owner_id == current_user.id).first()
    if not trafo:
        raise HTTPException(status_code=404, detail="Trafo not found")
    trafo_schema = schemas.TrafoDetail.model_validate(trafo)
    trafo_data = trafo_schema.model_dump()
    return response_ok(data=trafo_data)

# UPDATE BY ID
@router.post("/trafo/update/{id}", response_model=schemas.Trafo)
def update_trafo(id: int, trafo: schemas.TrafoCreate, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    db_trafo = db.query(models.Trafo).filter(models.Trafo.id == id, models.Trafo.owner_id == current_user.id).first()
    if not db_trafo:
        raise HTTPException(status_code=404, detail="Trafo not found")
    for key, value in trafo.dict().items():
        setattr(db_trafo, key, value)
    db.commit()
    db.refresh(db_trafo)
    return response_ok(data=None, message="Trafo updated")

# DELETE BY ID
@router.post("/trafo/delete/{id}")
def delete_trafo_by_id(id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    db_trafo = db.query(models.Trafo).filter(models.Trafo.id == id, models.Trafo.owner_id == current_user.id).first()
    if not db_trafo:
        raise HTTPException(status_code=404, detail="Trafo not found")
    db.delete(db_trafo)
    db.commit()
    return response_ok(data=None, message="Trafo deleted")
