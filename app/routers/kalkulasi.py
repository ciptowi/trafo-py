from fastapi import Query, Depends, APIRouter, UploadFile
from fastapi.params import File
from sqlalchemy.orm import Session

from app.services import kalkulasi_service
from app.core.database import get_db
from app.schemas.hasil_kalkulasi_scema import TrafoHasilKalkulasi

router = APIRouter(tags=["hasil kalkulasi"])

@router.post("/kalkulasi/upload-csv")
async def upload_hasil_kalkulasi(
    id_trafo: int = Query(..., description="ID Trafo yang akan di-upload datanya"),
    kapasitas: int = Query(..., description="Kapasitas Trafo"), 
    file: UploadFile = File(...), 
    db: Session = Depends(get_db), 
):
    return await kalkulasi_service.upload_hasil_kalkulasi2(id_trafo=id_trafo, kapasitas=kapasitas, file=file, db=db)

@router.get("/trafo/{trafo_id}/hasil-kalkulasi", response_model=TrafoHasilKalkulasi)
def get_trafo_hasil_kalkulasi_by_id(trafo_id: int, db: Session = Depends(get_db)):
    return kalkulasi_service.get_trafo_hasil_kalkulasi_by_id(trafo_id=trafo_id, db=db)

@router.get("/kalkulasi/export-csv/{trafo_id}", responses={
    200: {"description": "Success export csv", "content": {"text/csv": {"example": ""}}},
    404: {"description": "Trafo not found"}
    })
def export_csv_by_id_trafo(trafo_id: int, db: Session = Depends(get_db)):
    return kalkulasi_service.export_csv_by_id_trafo(trafo_id=trafo_id, db=db)
