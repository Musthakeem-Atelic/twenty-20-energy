from sqlalchemy import Column, Integer, String, Float, DateTime, Date, func, JSON, Enum, Index
from shared.database import Base
import enum


class FrequencyEnum(enum.Enum):
    DAILY   = "DAILY"
    MONTHLY = "MONTHLY"
    WEEKLY  = "WEEKLY"
    ANNUAL  = "ANNUAL"


class NaturalGasPrice(Base):
    __tablename__ = 'natural_gas_price'

    id = Column(Integer, primary_key=True, autoincrement=True)
    source = Column(String, nullable=False, index=True, default="EIA")
    
    period = Column(Date, nullable=False, index=True)          # trading/price date
    duoarea = Column(String, index=True)                       # area code (e.g., "RGC")
    area_name = Column(String)                                 # area name (e.g., "NA")
    product = Column(String)                                   # product code (e.g., "EPG0")
    product_name = Column(String)                              # product description
    process = Column(String)                                   # process code (e.g., "PS0")
    process_name = Column(String)                              # process description (e.g., "Spot Price")
    series = Column(String, index=True)                        # series ID (e.g., "RNGWHHD")
    series_description = Column(String)                        # full description
    value = Column(Float, nullable=False)                      # price as float
    units = Column(String)                                     # e.g., "$/MMBTU"
    frequency = Column(Enum(FrequencyEnum), default=FrequencyEnum.DAILY)
    
    # Metadata
    raw_metadata = Column(JSON)                                # store full response data if needed
    api_version = Column(String)                               # from response.apiVersion
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Optional: add composite index for fast lookups by series and date
    __table_args__ = (
        Index('idx_series_period', 'series', 'period', unique=False),
    )