from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services import dashboard_service

router = APIRouter(tags=["dashboard"])

@router.get("/dashboard/total-trafo", response_model=dict)
def total_trafo(db: Session = Depends(get_db)):
    return dashboard_service.total_trafo_per_group_trafo(db=db)

@router.get("/dashboard/trafo-all", response_model=dict)
def trafo_list(db: Session = Depends(get_db)):
    return dashboard_service.list_all_trafo(db=db)

@router.get("/dashboard/forecast-vs-actual/{id}", response_model=dict)
def forecast_vs_actual(id: int, db: Session = Depends(get_db)):
    return dashboard_service.forecast_vs_actual(id=id, db=db)
