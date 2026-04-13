from sqlalchemy import Column, Integer, String, Float, DateTime, func
from geoalchemy2 import Geometry
from shared.database import Base

class WetlandDetail(Base):
    __tablename__ = 'wetland_details'

    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Core Attributes from GDB
    external_id = Column(String, unique=True, index=True, nullable=True)
    wetland_type = Column(String, nullable=True)
    classification_code = Column(String, index=True, nullable=True)
    size_acres = Column(Float, nullable=True)
    
    # Metadata for Lineage
    state = Column(String(2), nullable=False, index=True)
    source = Column(String, nullable=False, index=True)
    

    geom = Column(Geometry(geometry_type='MULTIPOLYGON', srid=4326), nullable=False)
    
    # Audit trail
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())