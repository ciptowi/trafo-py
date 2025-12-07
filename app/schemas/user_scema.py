from pydantic import BaseModel

class UserBase(BaseModel):
    username: str

class UserCreate(UserBase):
    password: str

class User(UserBase):
    id: int
    class Config:
        from_attributes = True
    
class UserView(UserBase):
    id: int
    class Config:
        from_attributes = True
        
class UserUpdateUsername(UserBase):
    username: str
    class Config:
        from_attributes = True
    
class UserUpdatePassword(BaseModel):
    oldPassword: str
    password: str
    class Config:
        from_attributes = True
