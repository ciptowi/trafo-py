from fastapi import Depends, Query, HTTPException
from sqlalchemy.orm import Session

from app.core.database import Base, engine, get_db
from app.dependencies.response import response_ok, response_paginate
from app.models.group_trafo_model import GroupTrafo
from app.models.user_model import User
from app.dependencies.auth import get_current_user
from app.schemas.group_trafo_scema import GroupTrafoCreate, GroupTrafoCombobox, GroupTrafo as GroupTrafoSchema

import math

# Create table 'group trafo' when not exist
Base.metadata.create_all(bind=engine, tables=[GroupTrafo.__table__])

# app/services/group_trafo_service.py

def can_view_all_group(user: User) -> bool:
    if user.username.lower() == "admin":
        return True

    gid = user.group_id

    if gid is None:
        return True

    gid = gid.strip()
    if gid == "":
        return True

    if "UP3" in gid:
        return True

    return False

def create_group_trafo(group_trafo: GroupTrafoCreate, db: Session):
    new_group_trafo = GroupTrafo(**group_trafo.dict())
    db.add(new_group_trafo)
    db.commit()
    db.refresh(new_group_trafo)
    return response_ok(data=None, message="Group Trafo created")

def read_all_trafo_group(db: Session, q: str | None = Query(None, description="Cari berdasarkan nama"),
    page: int = 0,
    size: int = 10,
):
    base_query = db.query(GroupTrafo)
    if q:
        base_query = base_query.filter(GroupTrafo.name.contains(q))
    total = base_query.count()
    totalPage = math.ceil(total / size) if total > 0 else 0
    list_of_trafo_group_models = base_query.offset(page * size).limit(size).all()
    data_for_response = [GroupTrafoSchema.model_validate(group).model_dump() for group in list_of_trafo_group_models]    
    return response_paginate(data_for_response, page, size, total, totalPage)

def update_group_trafo(id: int, group_trafo: GroupTrafoCreate, db: Session):
    db_group_trafo = db.query(GroupTrafo).filter(GroupTrafo.id == id).first()
    if not db_group_trafo:
        raise HTTPException(status_code=404, detail="Group Trafo not found")
    for key, value in group_trafo.dict().items():
        setattr(db_group_trafo, key, value)
    db.commit()
    db.refresh(db_group_trafo)
    return response_ok(data=None, message="Group Trafo updated")

def delete_group_trafo_by_id(id: int, db: Session):
    db_group_trafo = db.query(GroupTrafo).filter(GroupTrafo.id == id).first()
    if not db_group_trafo:
        raise HTTPException(status_code=404, detail="Group Trafo not found")
    db.delete(db_group_trafo)
    db.commit()
    return response_ok(data=None, message=f"Group Trafo {id} deleted")
def read_trafo_group_combobox(
    db: Session,
    current_user: User
):
    query = db.query(GroupTrafo)

    if not can_view_all_group(current_user):
        query = query.filter(GroupTrafo.id == current_user.group_id)

    combobox = [
        GroupTrafoCombobox(
            id=g.id,
            name=g.name
        ).model_dump()
        for g in query.all()
    ]

    return response_ok(data=combobox)
