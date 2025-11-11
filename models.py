from sqlalchemy import Column, DateTime, Float, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    password = Column(String)

    items = relationship("Item", back_populates="owner")
    trafo = relationship("Trafo", back_populates="owner")

class Item(Base):
    __tablename__ = "items"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    description = Column(String, nullable=True)
    owner_id = Column(Integer, ForeignKey("users.id"))

    owner = relationship("User", back_populates="items")

class Trafo(Base):
    __tablename__ = "trafo"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    type = Column(String, nullable=False)
    brand = Column(String, nullable=False)
    kapasitas = Column(Integer, nullable=False)
    voltase = Column(Integer, nullable=False)
    current = Column(Integer, nullable=False)
    phasa = Column(String, nullable=False)
    longitude = Column(Float, nullable=False)
    latitude = Column(Float, nullable=False)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    group_id = Column(Integer, ForeignKey("group_trafo.id"), nullable=True)

    owner = relationship("User", back_populates="trafo")
    group = relationship("GroupTrafo", back_populates="trafo")
    hasil_kalkulasi = relationship("HasilKalkulasi", back_populates="trafo")

class GroupTrafo(Base):
    __tablename__ = "group_trafo"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    kodegrup = Column(String, nullable=False)
    
    trafo = relationship("Trafo", back_populates="group")

class HasilKalkulasi(Base):
    __tablename__ = "hasil_kalkulasi"

    id = Column(Integer, primary_key=True, index=True)
    id_trafo = Column(Integer, ForeignKey("trafo.id"), nullable=False)
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
