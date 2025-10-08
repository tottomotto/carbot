"""Database models for the car platform."""
from datetime import datetime
from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    JSON,
    Float,
    Boolean,
    Text,
    ForeignKey,
    CheckConstraint,
    UniqueConstraint,
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class Manufacturer(Base):
    """Canonical data for a car manufacturer."""
    __tablename__ = "manufacturers"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False, unique=True, index=True)
    models = relationship("Model", back_populates="manufacturer")

    def __repr__(self):
        return f"<Manufacturer(id={self.id}, name='{self.name}')>"


class Model(Base):
    """Canonical data for a car model."""
    __tablename__ = "models"
    id = Column(Integer, primary_key=True, autoincrement=True)
    manufacturer_id = Column(Integer, ForeignKey("manufacturers.id"), nullable=False)
    name = Column(String(100), nullable=False, index=True)
    manufacturer = relationship("Manufacturer", back_populates="models")
    variants = relationship("Variant", back_populates="model")
    __table_args__ = (UniqueConstraint("manufacturer_id", "name", name="uq_model_manufacturer_name"),)

    def __repr__(self):
        return f"<Model(id={self.id}, name='{self.name}')>"


class Variant(Base):
    """Canonical data for a specific car variant."""
    __tablename__ = "variants"
    id = Column(Integer, primary_key=True, autoincrement=True)
    model_id = Column(Integer, ForeignKey("models.id"), nullable=False)
    name = Column(String(100), nullable=False, index=True)
    start_year = Column(Integer)
    end_year = Column(Integer)
    model = relationship("Model", back_populates="variants")
    unique_cars = relationship("UniqueCar", back_populates="variant")
    images = relationship("Image", back_populates="variant") # for generic variant images
    __table_args__ = (UniqueConstraint("model_id", "name", name="uq_variant_model_name"),)

    def __repr__(self):
        return f"<Variant(id={self.id}, name='{self.name}')>"


class UniqueCar(Base):
    """Master record for a single, physical car, identified through deduplication."""
    __tablename__ = "unique_cars"
    id = Column(Integer, primary_key=True, autoincrement=True)
    variant_id = Column(Integer, ForeignKey("variants.id"), nullable=False)
    vin = Column(String(17), unique=True, nullable=True, index=True)
    first_seen_at = Column(DateTime, default=datetime.utcnow)
    last_seen_at = Column(DateTime, default=datetime.utcnow)
    status = Column(String(50), default="For Sale", index=True)
    variant = relationship("Variant", back_populates="unique_cars")
    ads = relationship("Ad", back_populates="unique_car")
    images = relationship("Image", back_populates="unique_car") # for specific car images

    def __repr__(self):
        return f"<UniqueCar(id={self.id}, variant_id={self.variant_id})>"


class Ad(Base):
    """An advertisement for a car on a specific website."""
    __tablename__ = "ads"
    id = Column(Integer, primary_key=True, autoincrement=True)
    unique_car_id = Column(Integer, ForeignKey("unique_cars.id"), nullable=True, index=True)
    source_site = Column(String(100), nullable=False, index=True)
    source_id = Column(String(255), nullable=False, index=True)
    source_url = Column(Text, nullable=False, unique=True)
    # Store raw text fields for later enrichment and validation
    raw_title = Column(String(500))
    raw_price = Column(Float)
    raw_year = Column(Integer)
    raw_make = Column(String(100))
    raw_model = Column(String(100))
    raw_location = Column(String(255))
    raw_data = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_scraped_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    unique_car = relationship("UniqueCar", back_populates="ads")
    images = relationship("Image", back_populates="ad")
    __table_args__ = (UniqueConstraint("source_site", "source_id", name="uq_ad_source"),)

    def __repr__(self):
        return f"<Ad(id={self.id}, source_site='{self.source_site}', source_id='{self.source_id}')>"


class Image(Base):
    """A universal repository for all images, regardless of source."""
    __tablename__ = "images"
    id = Column(Integer, primary_key=True, autoincrement=True)
    # Foreign keys to define the image's context
    ad_id = Column(Integer, ForeignKey("ads.id"), nullable=True)
    variant_id = Column(Integer, ForeignKey("variants.id"), nullable=True)
    unique_car_id = Column(Integer, ForeignKey("unique_cars.id"), nullable=True)
    
    # Storage and metadata
    image_uri = Column(String(1024), nullable=False, unique=True)
    checksum = Column(String(64), nullable=False, unique=True, index=True)
    status = Column(String(50), default="raw", index=True)
    annotations = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    ad = relationship("Ad", back_populates="images")
    variant = relationship("Variant", back_populates="images")
    unique_car = relationship("UniqueCar", back_populates="images")
    
    __table_args__ = (
        CheckConstraint(
            "(ad_id IS NOT NULL)::integer + "
            "(variant_id IS NOT NULL)::integer + "
            "(unique_car_id IS NOT NULL)::integer = 1",
            name="chk_image_source_exclusive"
        ),
    )

    def __repr__(self):
        return f"<Image(id={self.id}, uri='{self.image_uri}', status='{self.status}')>"

