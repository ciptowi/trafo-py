from datetime import datetime
from pydantic import BaseModel
from typing import Optional
from app.schemas.trafo_scema import TrafoDetail

class HasilKalkulasiBase(BaseModel):
    v_r: float
    v_s: float
    v_t: float
    i_r: float
    i_s: float
    i_t: float
    cosphi: float
    kv_r: float
    kv_s: float
    kv_t: float
    kw_r: float
    kw_s: float
    kw_t: float
    kvar_r: float
    kvar_s: float
    kvar_t: float
    total_kva: float
    total_kw: float
    total_kvar: float
    sisa_kap: float
    waktu_kalkulasi: datetime
    tgl_upload: datetime

class HasilKalkulasiCreate(HasilKalkulasiBase):
    pass

class HasilKalkulasi(HasilKalkulasiBase):
    id: int
    class Config:
        from_attributes = True


class TrafoHasilKalkulasi(BaseModel):
    trafo: TrafoDetail
    hasil_kalkulasi: Optional[HasilKalkulasi] = None
    class Config:
        from_attributes = True