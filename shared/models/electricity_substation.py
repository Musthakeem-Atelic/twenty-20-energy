from sqlalchemy import Column, Integer, String, Float, DateTime, func, JSON
from geoalchemy2 import Geometry
from shared.database import Base

class ElectricitySubstation(Base):
    __tablename__ = 'electricity_substation'

    id = Column(Integer, primary_key=True, autoincrement=True)
    source = Column(String, nullable=False, index=True)

    # Core identity
    osm_id            = Column(String, index=True)       # e.g. "relation/13685176"
    name              = Column(String)                    # e.g. "Elza Substation"
    ref               = Column(String)                    # short reference code, e.g. "SP", "PS"

    # Operator info
    operator          = Column(String)                    # e.g. "Knoxville Utilities Board"
    operator_short    = Column(String)                    # e.g. "KUB", "TVA"
    operator_wikidata = Column(String)                    # e.g. "Q109923505"
    operator_wikipedia= Column(String)                    # e.g. "en:Tennessee Valley Authority"

    # Electrical characteristics
    voltage           = Column(Float)                     # in Volts, e.g. 161000.0
    substation_type   = Column(String)                    # transmission / distribution / generation
    location          = Column(String)                    # outdoor / indoor / underground

    # Administrative / geographic context
    state_name        = Column(String)
    state_iso         = Column(String)
    country           = Column(String)

    # Raw properties preserved for forward compatibility
    raw_metadata      = Column(JSON)

    # Geometry (polygon footprint in WGS84)
    geom = Column(
        Geometry(geometry_type='POLYGON', srid=4326, spatial_index=True),
        nullable=False
    )

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())