"""Pydantic schemas for API request/response models."""
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class CarAdResponse(BaseModel):
    """Response model for car ad."""
    
    id: int
    source_site: str
    source_id: str
    source_url: str
    title: Optional[str] = None
    price: Optional[float] = None
    currency: Optional[str] = None
    year: Optional[int] = None
    make: Optional[str] = None
    model: Optional[str] = None
    mileage: Optional[int] = None
    location: Optional[str] = None
    dealer_name: Optional[str] = None
    dealer_type: Optional[str] = None
    fuel_type: Optional[str] = None
    transmission: Optional[str] = None
    body_type: Optional[str] = None
    color: Optional[str] = None
    engine_power: Optional[int] = None
    engine_displacement: Optional[float] = None
    image_urls: Optional[List[str]] = None
    local_image_paths: Optional[List[str]] = None
    scraped_at: datetime
    is_active: bool
    is_processed: bool

    class Config:
        from_attributes = True


class CarAdEnrichedResponse(BaseModel):
    """Response model for enriched car ad."""
    
    id: int
    raw_ad_id: int
    canonical_make: Optional[str] = None
    canonical_model: Optional[str] = None
    generation: Optional[str] = None
    trim: Optional[str] = None
    body_type: Optional[str] = None
    engine_type: Optional[str] = None
    engine_displacement: Optional[float] = None
    horsepower: Optional[int] = None
    transmission: Optional[str] = None
    drivetrain: Optional[str] = None
    fuel_type: Optional[str] = None
    features: Optional[List[str]] = None
    colors: Optional[Dict[str, str]] = None
    data_quality_score: Optional[float] = None
    is_validated: bool
    matched_official_data: bool
    official_data_source: Optional[str] = None
    enriched_at: datetime

    class Config:
        from_attributes = True


class OfficialCarDataResponse(BaseModel):
    """Response model for official car data."""
    
    id: int
    make: str
    model: str
    year: int
    generation: Optional[str] = None
    trim: Optional[str] = None
    specs: Optional[Dict[str, Any]] = None
    available_features: Optional[List[str]] = None
    available_colors: Optional[List[str]] = None
    data_source: Optional[str] = None
    fetched_at: datetime

    class Config:
        from_attributes = True

