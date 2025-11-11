from datetime import datetime
from pydantic import BaseModel, ConfigDict

# --- USER ---
class UserBase(BaseModel):
    username: str

class UserCreate(UserBase):
    password: str

class User(UserBase):
    id: int
    class Config:
        from_attributes = True

# --- TRAFO ---
class TrafoBase(BaseModel):
    group_id: int
    name: str
    type: str
    brand: str
    kapasitas: int
    voltase: int
    current: int
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
        
# --- GROUP TRAFO ---
class GroupTrafoBase(BaseModel):
    name: str
    kodegrup: str

class GroupTrafoCreate(GroupTrafoBase):
    pass

class GroupTrafo(GroupTrafoBase):
    id: int
    class Config:
        from_attributes = True

# --- Combobox ---
class Combobox(BaseModel):
    id: int
    name: str

# --- HASIL KALKULASI ---
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
    sisakap: float
    waktu_kalkulasi: datetime
    tgl_upload: datetime

class HasilKalkulasiCreate(HasilKalkulasiBase):
    pass

class HasilKalkulasi(HasilKalkulasiBase):
    id: int
    class Config:
        from_attributes = True
