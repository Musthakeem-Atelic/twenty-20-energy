from sqlalchemy import Column, Integer, String, Float, DateTime, func, JSON
from geoalchemy2 import Geometry
from shared.database import Base

class ElectricityTransmissionLine(Base):
    __tablename__ = 'electricity_transmission_line'

    id = Column(Integer, primary_key=True, autoincrement=True)
    source = Column(String, nullable=False, index=True)

    # Core fields mapped from GeoJSON properties
    line_id       = Column(String)
    owner         = Column(String)
    status        = Column(String)
    line_type     = Column(String)   # OVERHEAD / UNDERGROUND
    voltage       = Column(Float)
    volt_class    = Column(String)
    sub_1         = Column(String)
    sub_2         = Column(String)
    inferred      = Column(String)

    state_name    = Column(String)
    state_iso     = Column(String)

    raw_metadata  = Column(JSON)

    geom = Column(
        Geometry(geometry_type='GEOMETRY', srid=4326, spatial_index=True),
        nullable=False
    )

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())