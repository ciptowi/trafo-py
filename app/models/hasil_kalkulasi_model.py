from sqlalchemy import Column, Integer, Float, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from app.core.database import Base

class HasilKalkulasi(Base):
    __tablename__ = "hasil_kalkulasi"

    id = Column(Integer, primary_key=True, index=True)
    id_trafo = Column(Integer, ForeignKey("trafo.id"), nullable=False)
    importwh = Column(Float, nullable=False)
    exportwh = Column(Float, nullable=False)
    importvarh = Column(Float, nullable=False)
    exportvarh = Column(Float, nullable=False)
    v_r = Column(Float, nullable=False)
    v_s = Column(Float, nullable=False)
    v_t = Column(Float, nullable=False)
    i_r = Column(Float, nullable=False)
    i_s = Column(Float, nullable=False)
    i_t = Column(Float, nullable=False)
    cosphi = Column(Float, nullable=False)
    kv_r = Column(Float, nullable=True)
    kv_s = Column(Float, nullable=True)
    kv_t = Column(Float, nullable=True)
    kw_r = Column(Float, nullable=True)
    kw_s = Column(Float, nullable=True)
    kw_t = Column(Float, nullable=True)
    kvar_r = Column(Float, nullable=True)
    kvar_s = Column(Float, nullable=True)
    kvar_t = Column(Float, nullable=True)
    total_kva = Column(Float, nullable=True)
    total_kw = Column(Float, nullable=True)
    total_kvar = Column(Float, nullable=True)
    sisa_kap = Column(Float, nullable=True)        
    waktu_kalkulasi = Column(DateTime, nullable=True)
    tgl_upload = Column(DateTime, nullable=True)

    trafo = relationship("Trafo", back_populates="hasil_kalkulasi")
