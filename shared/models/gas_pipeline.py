from sqlalchemy import Column, Integer, String, Float, DateTime, func, JSON
from geoalchemy2 import Geometry
from shared.database import Base

class NaturalGasPipeline(Base):
    __tablename__ = 'natural_gas_pipeline'

    id = Column(Integer, primary_key=True, autoincrement=True)
    source = Column(String, nullable=False, index=True)
    
    # Core Standardized Fields
    operator = Column(String)
    status = Column(String)
    pipeline_type = Column(String) 
    diameter_inches = Column(Float)
    
    state_name = Column(String)
    state_iso = Column(String)
    
    raw_metadata = Column(JSON) 
    
    geom = Column(Geometry(geometry_type='MULTILINESTRING', srid=4326, spatial_index=True), nullable=False)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())