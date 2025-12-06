from pydantic import BaseModel
from datetime import datetime

class ForecastResult(BaseModel):
    id: int
    id_trafo: int
    tanggal_forecast: datetime
    hasil_forecast: float
