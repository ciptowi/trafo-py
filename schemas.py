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
