from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship
from app.core.database import Base

class GroupTrafo(Base):
    __tablename__ = "group_trafo"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    kodegrup = Column(String, nullable=False)
    
    trafo = relationship("Trafo", back_populates="group")
    users = relationship("User", back_populates="group")