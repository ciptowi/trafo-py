from pydantic import BaseModel, ConfigDict
from app.schemas.group_trafo_scema import GroupTrafo

class TrafoBase(BaseModel):
    group_id: int
    name: str
    type: str
    brand: str
    kapasitas: int
    voltase: int
    current: int
    voltase_per: int
    current_per: int
    phasa: str
    longitude: float
    latitude: float

class TrafoCreate(TrafoBase):
    pass

class Trafo(TrafoBase):
    id: int
    class Config:
        from_attributes = True
        
class TrafoDetail(TrafoBase):
    group: GroupTrafo | None = None
    model_config = ConfigDict(from_attributes=True)