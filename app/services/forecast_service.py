from fastapi import HTTPException
from sqlalchemy.orm import Session
from app.dependencies.response import response_ok
from app.models.hasil_kalkulasi_model import HasilKalkulasi
from app.services.forecast_formula import ForecastFormula

def forecast_trafo(trafo_id: int, db: Session):
    try:
        
        formula = ForecastFormula(db=db, trafo_id=trafo_id)
        return formula.train_model()

    except Exception as e:
        print(f"Error internal: {e}") # Tambahkan print untuk debugging
        raise HTTPException(status_code=500, detail=f"Error internal: {e}")