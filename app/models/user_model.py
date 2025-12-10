from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from app.core.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    password = Column(String)
    group_id = Column(Integer, ForeignKey("group_trafo.id"), nullable=True)
    
    group = relationship("GroupTrafo", back_populates="users")
