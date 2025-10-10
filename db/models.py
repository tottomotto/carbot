"""Database models for the car platform."""
from sqlalchemy import (
    Column, Integer, String, Text, ForeignKey, REAL, JSON
)
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.dialects.postgresql import JSONB

Base = declarative_base()


class Brand(Base):
    __tablename__ = "brands"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False, unique=True)
    country = Column(String(50))
    url = Column(Text)
    models = relationship("Model", back_populates="brand", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Brand(id={self.id}, name='{self.name}')>"


class Model(Base):
    __tablename__ = "models"
    id = Column(Integer, primary_key=True, autoincrement=True)
    brand_id = Column(Integer, ForeignKey("brands.id"), nullable=False)
    name = Column(String(100), nullable=False)
    body_type = Column(String(50))
    start_year = Column(Integer)
    end_year = Column(Integer)
    url = Column(Text)
    brand = relationship("Brand", back_populates="models")
    generations = relationship("Generation", back_populates="model", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Model(id={self.id}, name='{self.name}')>"


class Generation(Base):
    __tablename__ = "generations"
    id = Column(Integer, primary_key=True, autoincrement=True)
    model_id = Column(Integer, ForeignKey("models.id"), nullable=False)
    code = Column(String(20))
    gen_name = Column(String(100))
    start_year = Column(Integer)
    end_year = Column(Integer)
    description = Column(Text)
    url = Column(Text)
    model = relationship("Model", back_populates="generations")
    versions = relationship("Version", back_populates="generation", cascade="all, delete-orphan")
    documents = relationship("Document", back_populates="generation", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Generation(id={self.id}, code='{self.code}', name='{self.gen_name}')>"


class Version(Base):
    __tablename__ = "versions"
    id = Column(Integer, primary_key=True, autoincrement=True)
    generation_id = Column(Integer, ForeignKey("generations.id"), nullable=False)
    version_name = Column(String(100))
    production_years = Column(String(20))
    engine_type = Column(String(50))
    engine_details = Column(Text)
    url = Column(Text)
    generation = relationship("Generation", back_populates="versions")
    spec = relationship("Spec", back_populates="version", uselist=False, cascade="all, delete-orphan")
    images = relationship("Image", back_populates="version", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Version(id={self.id}, name='{self.version_name}')>"


class Spec(Base):
    __tablename__ = "specs"
    id = Column(Integer, primary_key=True, autoincrement=True)
    version_id = Column(Integer, ForeignKey("versions.id"), nullable=False, unique=True)
    
    # Engine - Basic
    cylinders = Column(String(20))
    displacement_cc = Column(Integer)  # Cubic centimeters
    displacement_l = Column(REAL)      # Liters
    
    # Power - Multiple units
    power_hp = Column(Integer)         # Horsepower (metric)
    power_kw = Column(Integer)         # Kilowatts
    power_bhp = Column(Integer)        # Brake horsepower
    power_rpm = Column(Integer)        # RPM at max power
    
    # Torque - Multiple units
    torque_nm = Column(Integer)        # Newton-meters
    torque_lb_ft = Column(Integer)     # Pound-feet
    torque_rpm_min = Column(Integer)   # Min RPM for max torque
    torque_rpm_max = Column(Integer)   # Max RPM for max torque
    
    # Fuel
    fuel_type = Column(String(20))
    fuel_capacity_l = Column(REAL)     # Liters
    fuel_capacity_gal = Column(REAL)   # Gallons (US)
    
    # Performance
    top_speed_kph = Column(Integer)    # km/h
    top_speed_mph = Column(Integer)    # mph
    acceleration_0_100_kph = Column(REAL)  # seconds (0-100 km/h)
    acceleration_0_60_mph = Column(REAL)   # seconds (0-60 mph)
    
    # Drivetrain
    transmission = Column(String(50))
    drive_type = Column(String(50))
    
    # Brakes & Tires
    brake_type_front = Column(String(50))
    brake_type_rear = Column(String(50))
    tire_size_front = Column(String(50))
    tire_size_rear = Column(String(50))
    
    # Dimensions
    length_mm = Column(Integer)
    length_in = Column(REAL)
    width_mm = Column(Integer)
    width_in = Column(REAL)
    height_mm = Column(Integer)
    height_in = Column(REAL)
    wheelbase_mm = Column(Integer)
    wheelbase_in = Column(REAL)
    ground_clearance_mm = Column(Integer)
    ground_clearance_in = Column(REAL)
    
    # Weight
    unladen_weight_kg = Column(Integer)
    unladen_weight_lbs = Column(Integer)
    gross_weight_kg = Column(Integer)
    gross_weight_lbs = Column(Integer)
    
    # Cargo
    cargo_volume_l = Column(Integer)
    cargo_volume_cuft = Column(REAL)
    
    # Aerodynamics & Handling
    aerodynamics_cd = Column(REAL)
    turning_circle_m = Column(REAL)
    
    # Fuel Economy
    fuel_economy_city_l_100km = Column(REAL)
    fuel_economy_city_mpg = Column(REAL)
    fuel_economy_highway_l_100km = Column(REAL)
    fuel_economy_highway_mpg = Column(REAL)
    fuel_economy_combined_l_100km = Column(REAL)
    fuel_economy_combined_mpg = Column(REAL)
    
    # Emissions
    co2_emissions_g_km = Column(Integer)
    
    # Extra data (infotainment, features, unmapped specs)
    extra = Column(JSONB)
    
    version = relationship("Version", back_populates="spec")


class Image(Base):
    __tablename__ = "images"
    id = Column(Integer, primary_key=True, autoincrement=True)
    version_id = Column(Integer, ForeignKey("versions.id"), nullable=False)
    url = Column(Text, nullable=False)
    caption = Column(String(255))
    version = relationship("Version", back_populates="images")


class Document(Base):
    __tablename__ = "documents"
    id = Column(Integer, primary_key=True, autoincrement=True)
    generation_id = Column(Integer, ForeignKey("generations.id"), nullable=False)
    doc_type = Column(String(50))
    url = Column(Text)
    generation = relationship("Generation", back_populates="documents")

