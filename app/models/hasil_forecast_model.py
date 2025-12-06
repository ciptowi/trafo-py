from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from app.core.database import Base


class HasilForecast(Base):
    __tablename__ = "hasil_forecast"

    id = Column(Integer, primary_key=True, index=True)
    id_trafo = Column(Integer, ForeignKey("trafo.id"))
    tanggal_forecast = Column(DateTime)
    hasil_forecast = Column(Float)

    trafo = relationship("Trafo", lazy="joined")
