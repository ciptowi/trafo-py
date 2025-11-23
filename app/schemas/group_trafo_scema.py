from pydantic import BaseModel

class GroupTrafoBase(BaseModel):
    name: str
    kodegrup: str

class GroupTrafoCreate(GroupTrafoBase):
    pass

class GroupTrafo(GroupTrafoBase):
    id: int
    class Config:
        from_attributes = True
        
class GroupTrafoCombobox(BaseModel):
    id: int
    name: str