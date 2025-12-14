from fastapi import HTTPException, Query
from sqlalchemy.orm import Session, joinedload

from app.core.database import Base, engine
from app.dependencies.response import response_ok, response_paginate
from app.models.trafo_model import Trafo
from app.models.user_model import User
from app.schemas.trafo_scema import TrafoCreate, Trafo as TrafoSchema, TrafoDetail

import math
        
# Create table 'trafo' when not exist
Base.metadata.create_all(bind=engine, tables=[Trafo.__table__])

def create_trafo(
    trafo: TrafoCreate,
    db: Session,
    user: User
):
    # admin boleh semua
    if user.username.lower() == "admin":
        pass

    # user group_id NULL → boleh semua
    elif user.group_id is None:
        pass

    # user biasa → hanya group sendiri
    elif user.group_id != trafo.group_id:
        raise HTTPException(status_code=403, detail="Forbidden")

    new_trafo = Trafo(**trafo.model_dump())
    db.add(new_trafo)
    db.commit()
    db.refresh(new_trafo)

    return response_ok(message="Trafo created")



def read_all_trafo(user: User,db: Session, q: str | None = Query(None, description="Cari berdasarkan nama"),
    groupId: int = Query(description="ID Group Trafo wajib"),
    page: int = Query(0, description="Nomor halaman"),
    size: int = Query(10, description="Jumlah data per halaman"),
):
    group_id = user.group_id if user.group_id else groupId
    base_query = db.query(Trafo).filter(Trafo.group_id == group_id)
    if q:
        base_query = base_query.filter(Trafo.name.contains(q))
    total = base_query.count()
    totalPage = math.ceil(total / size) if total > 0 else 0
    list_of_trafo_models = base_query.offset(page * size).limit(size).all()
    data_for_response = [TrafoSchema.model_validate(trafo).model_dump() for trafo in list_of_trafo_models]    
    return response_paginate(data_for_response, page, size, total, totalPage)

def read_trafo(id: int, db: Session, user: User):
    trafo = db.query(Trafo).options(joinedload(Trafo.group)).filter(Trafo.id == id).first()
    if not trafo:
        raise HTTPException(status_code=404, detail="Trafo not found")
    if user.group_id and trafo.group_id != user.group_id:
        raise HTTPException(status_code=403, detail="Forbidden")
    trafo_schema = TrafoDetail.model_validate(trafo)
    trafo_data = trafo_schema.model_dump()
    return response_ok(data=trafo_data)

def update_trafo(id: int, trafo: TrafoCreate, db: Session, user: User):
    db_trafo = db.query(Trafo).filter(Trafo.id == id).first()
    if not db_trafo:
        raise HTTPException(status_code=404, detail="Trafo not found")
    if user.group_id and db_trafo.group_id != user.group_id:
        raise HTTPException(status_code=403, detail="Forbidden")
    for key, value in trafo.dict().items():
        setattr(db_trafo, key, value)
    db.commit()
    db.refresh(db_trafo)
    return response_ok(data=None, message="Trafo updated")

def delete_trafo_by_id(id: int, db: Session, user: User):
    db_trafo = db.query(Trafo).filter(Trafo.id == id).first()
    if not db_trafo:
        raise HTTPException(status_code=404, detail="Trafo not found")
    if user.group_id and db_trafo.group_id != user.group_id:
        raise HTTPException(status_code=403, detail="Forbidden")
    db.delete(db_trafo)
    db.commit()
    return response_ok(data=None, message="Trafo deleted")
