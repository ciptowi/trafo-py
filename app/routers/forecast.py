from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.services import forecast_service

router = APIRouter(tags=["forecast"])

@router.get("/forecast/hitung/{trafo_id}", response_model=dict)
def forecast_trafo(trafo_id: int, db: Session = Depends(get_db)):
    return forecast_service.forecast_trafo(trafo_id=trafo_id, db=db)
