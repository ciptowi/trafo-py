from fastapi import FastAPI, Depends, HTTPException, APIRouter
from sqlalchemy.orm import Session
from database import engine, SessionLocal
from auth import router as auth_router, get_current_user

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
def create_group_trafo(group_trafo: schemas.GroupTrafoCreate, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    new_group_trafo = models.GroupTrafo(**group_trafo.dict(), owner_id=current_user.id)
    db.add(new_group_trafo)
    db.commit()
    db.refresh(new_group_trafo)
    return new_group_trafo

# DELETE GROUP TRAFO BY ID
@router.post("/group-trafo/delete/{id}")
def delete_group_trafo_by_id(id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    db_group_trafo = db.query(models.GroupTrafo).filter(models.GroupTrafo.id == id, models.GroupTrafo.owner_id == current_user.id).first()
    if not db_group_trafo:
        raise HTTPException(status_code=404, detail="Group Trafo not found")
    db.delete(db_group_trafo)
    db.commit()
    return {"message": f"Group Trafo {id} deleted"}
