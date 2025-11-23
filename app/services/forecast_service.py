from fastapi import HTTPException
from sqlalchemy.orm import Session
from app.dependencies.response import response_ok
from app.models.hasil_kalkulasi_model import HasilKalkulasi

def forecast_trafo(trafo_id: int, db: Session):
    try:
        hasil_kalkulasi = db.query(HasilKalkulasi).\
            filter(HasilKalkulasi.id_trafo == trafo_id).\
            order_by(HasilKalkulasi.waktu_kalkulasi.desc()).\
            first()

        if hasil_kalkulasi is None:
            raise HTTPException(status_code=404, detail=f"Hasil kalkulasi for trafo id {trafo_id} not found")
        
        data = {
            "datetime": hasil_kalkulasi.waktu_kalkulasi.strftime("%Y-%m-%d %H:%M:%S"),
            "hasil": hasil_kalkulasi.total_kva
        }

        return response_ok(
            data=data
        )

    except Exception as e:
        print(f"Error internal: {e}") # Tambahkan print untuk debugging
        raise HTTPException(status_code=500, detail=f"Error internal: {e}")