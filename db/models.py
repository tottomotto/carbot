"""Database models for car ads and enrichment."""
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, JSON, Float, Boolean, Text, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class CarAdRaw(Base):
    """Raw car ad data as scraped from sources."""

    __tablename__ = "car_ads_raw"

    id = Column(Integer, primary_key=True, autoincrement=True)
    source_site = Column(String(100), nullable=False, index=True)
    source_id = Column(String(255), nullable=False, index=True)
    source_url = Column(Text, nullable=False)
    
    # Raw scraped data
    raw_data = Column(JSON, nullable=False)
    
    # Basic extracted fields
    title = Column(String(500))
    price = Column(Float)
    currency = Column(String(10))
    year = Column(Integer, index=True)
    make = Column(String(100), index=True)
    model = Column(String(100), index=True)
    mileage = Column(Integer)
    location = Column(String(255))
    
    # Images
    image_urls = Column(JSON)  # List of image URLs
    
    # Metadata
    scraped_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Status
    is_active = Column(Boolean, default=True)
    is_processed = Column(Boolean, default=False)
    
    # Relationships
    enriched = relationship("CarAdEnriched", back_populates="raw_ad", uselist=False)

    def __repr__(self):
        return f"<CarAdRaw(id={self.id}, make={self.make}, model={self.model}, year={self.year})>"


class CarAdEnriched(Base):
    """Enriched car ad data with normalized and validated information."""

    __tablename__ = "car_ads_enriched"

    id = Column(Integer, primary_key=True, autoincrement=True)
    raw_ad_id = Column(Integer, ForeignKey("car_ads_raw.id"), nullable=False, unique=True)
    
    # Normalized fields
    canonical_make = Column(String(100), index=True)
    canonical_model = Column(String(100), index=True)
    generation = Column(String(50))
    trim = Column(String(100))
    body_type = Column(String(50))
    
    # Technical specs
    engine_type = Column(String(100))
    engine_displacement = Column(Float)  # in liters
    horsepower = Column(Integer)
    transmission = Column(String(50))
    drivetrain = Column(String(50))
    fuel_type = Column(String(50))
    
    # Features and options
    features = Column(JSON)  # List of features
    colors = Column(JSON)  # Exterior/interior colors
    
    # Validation flags
    data_quality_score = Column(Float)  # 0-1 score
    is_validated = Column(Boolean, default=False)
    validation_errors = Column(JSON)
    
    # Official data match
    matched_official_data = Column(Boolean, default=False)
    official_data_source = Column(String(100))
    
    # Metadata
    enriched_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    raw_ad = relationship("CarAdRaw", back_populates="enriched")

    def __repr__(self):
        return f"<CarAdEnriched(id={self.id}, make={self.canonical_make}, model={self.canonical_model})>"


class OfficialCarData(Base):
    """Official car specifications from OEM sources."""

    __tablename__ = "official_car_data"

    id = Column(Integer, primary_key=True, autoincrement=True)
    make = Column(String(100), nullable=False, index=True)
    model = Column(String(100), nullable=False, index=True)
    year = Column(Integer, nullable=False, index=True)
    generation = Column(String(50))
    trim = Column(String(100))
    
    # Specifications
    specs = Column(JSON)  # Full spec data
    available_features = Column(JSON)  # List of available features
    available_colors = Column(JSON)  # Available color options
    
    # Source
    data_source = Column(String(100))
    source_url = Column(Text)
    
    # Metadata
    fetched_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_current = Column(Boolean, default=True)

    def __repr__(self):
        return f"<OfficialCarData(make={self.make}, model={self.model}, year={self.year}, trim={self.trim})>"

