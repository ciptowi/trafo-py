from pydantic import BaseModel
from app.schemas.group_trafo_scema import GroupTrafo

class UserBase(BaseModel):
    username: str

class UserLogin(UserBase):
    password: str

class UserCreate(UserBase):
    group_id: int | None
    password: str

class User(UserBase):
    id: int
    class Config:
        from_attributes = True
    
class UserView(UserBase):
    id: int
    group: GroupTrafo | None = None
    class Config:
        from_attributes = True
        
class UserUpdateUsername(UserBase):
    username: str
    group_id: int | None
    class Config:
        from_attributes = True
    
class UserUpdatePassword(BaseModel):
    oldPassword: str
    password: str
    class Config:
        from_attributes = True
