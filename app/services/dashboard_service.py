from fastapi import HTTPException
from sqlalchemy.orm import Session, joinedload
from app.dependencies.response import response_ok
from app.models.trafo_model import Trafo
from app.models.hasil_forecast_model import HasilForecast
from app.models.hasil_kalkulasi_model import HasilKalkulasi
from app.models.group_trafo_model import GroupTrafo
from app.schemas.trafo_scema import TrafoListDashboard
from datetime import datetime

def total_trafo_per_group_trafo(db: Session):
    trafo_group = db.query(GroupTrafo).all()
    data = []
    for group in trafo_group:
        total_trafo = db.query(Trafo).filter(Trafo.group_id == group.id).count()
        data.append({
            "id": group.id,
            "name": group.name,
            "total_trafo": total_trafo
        })
    return response_ok(data=data)

def list_all_trafo(db: Session):
    trafo = db.query(Trafo).options(joinedload(Trafo.group)).all()
    trafo_schema = [TrafoListDashboard.model_validate(t, from_attributes=True) for t in trafo]
    trafo_data = [t.model_dump() for t in trafo_schema]
    return response_ok(data=trafo_data)

def forecast_vs_actual(id: int, db: Session):
    trafo = db.query(Trafo).filter(Trafo.id == id).first()
    if not trafo:
        raise HTTPException(status_code=404, detail="Trafo not found")
    forecast_results = db.query(HasilForecast).filter(HasilForecast.id_trafo == id).limit(20).all()
    if not forecast_results:
        raise HTTPException(status_code=404, detail="Trafo Forecast not found")
    calculated_results = db.query(HasilKalkulasi).filter(HasilKalkulasi.id_trafo == id).limit(20).all()
    if not calculated_results:
        raise HTTPException(status_code=404, detail="Trafo Calculated not found")
    
    trafo_name = trafo.name
    forecast_list = []
    calculated_list = []
    
    for item in forecast_results:
        tanggal_str = datetime.strftime(item.tanggal_forecast, "%Y-%m-%d %H:%M:%S")
        forecast_list.append({
            "datetime": tanggal_str, 
            "value": item.hasil_forecast,
        })
    
    for item in calculated_results:
        tanggal_str = datetime.strftime(item.waktu_kalkulasi, "%Y-%m-%d %H:%M:%S")
        calculated_list.append({
            "datetime": tanggal_str, 
            "value": (item.importwh / item.cosphi),
        })
    
    result = {
        "name": trafo_name,
        "forecast": forecast_list,
        "calculated": calculated_list
    }
    return response_ok(data=result)
    