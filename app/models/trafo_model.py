from sqlalchemy import Column, Integer, String, Float, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base

class Trafo(Base):
    __tablename__ = "trafo"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    type = Column(String, nullable=False)
    brand = Column(String, nullable=False)
    kapasitas = Column(Integer, nullable=False)
    voltase = Column(Integer, nullable=False)
    current = Column(Integer, nullable=False)
    voltase_per = Column(Integer, nullable=False)
    current_per = Column(Integer, nullable=False)
    phasa = Column(String, nullable=False)
    longitude = Column(Float, nullable=False)
    latitude = Column(Float, nullable=False)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    group_id = Column(Integer, ForeignKey("group_trafo.id"), nullable=True)

    owner = relationship("User", back_populates="trafo")
    group = relationship("GroupTrafo", back_populates="trafo")
    hasil_kalkulasi = relationship("HasilKalkulasi", back_populates="trafo")