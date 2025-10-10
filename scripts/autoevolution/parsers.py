"""Data parsing functions for AutoEvolution scraper."""
import re


def parse_specs(raw_specs: dict) -> dict:
    """Cleans and maps raw scraped spec data to the Spec model columns."""
    cleaned_specs = {}
    
    # Helper to extract numbers from strings or direct values
    def get_int(value):
        if value is None:
            return None
        # If already a number, convert to int
        if isinstance(value, (int, float)):
            return int(value)
        # If string, extract numbers
        if isinstance(value, str):
            nums = re.findall(r"[\d\.,]+", value)
            return int(re.sub(r"[\.,]", "", nums[0])) if nums else None
        return None

    def get_float(value):
        if value is None:
            return None
        # If already a number, convert to float
        if isinstance(value, (int, float)):
            return float(value)
        # If string, extract numbers
        if isinstance(value, str):
            nums = re.findall(r"[\d\.,]+", value)
            return float(nums[0].replace(",", ".")) if nums else None
        return None

    key_map = {
        # Engine specs
        "cylinders": "cylinders",
        "displacement": "displacement",
        "power": "horsepower",
        "torque": "torque",
        "fuel_system": "fuel_type",
        "fuel": "fuel_type",
        "fuel_type": "fuel_type",
        "fuel_tank_capacity": "fuel_capacity",
        "fuel_capacity": "fuel_capacity",
        
        # Performance specs
        "top_speed": "top_speed",
        "maximum_speed": "top_speed",
        "acceleration_0-62_mph_(0-100_km/h)": "acceleration_0_100",
        "acceleration_0-100_km/h_(0-62_mph)": "acceleration_0_100",
        "0-100_km/h": "acceleration_0_100",
        
        # Drivetrain specs
        "drive_train": "drive_type",
        "drivetrain": "drive_type",
        "drive_type": "drive_type",
        "transmission": "transmission",
        "gearbox": "transmission",
        
        # Brake specs
        "front_brakes": "brake_type_front",
        "rear_brakes": "brake_type_rear",
        "brakes_front": "brake_type_front",
        "brakes_rear": "brake_type_rear",
        
        # Tire specs
        "tire_size_front": "tire_size_front",
        "tire_size_rear": "tire_size_rear",
        "front_tire": "tire_size_front",
        "rear_tire": "tire_size_rear",
        
        # Dimensions
        "length": "length_mm",
        "width": "width_mm",
        "height": "height_mm",
        "wheelbase": "wheelbase_mm",
        "ground_clearance": "ground_clearance_mm",
        "min._ground_clearance": "ground_clearance_mm",
        
        # Weight
        "unladen_weight": "unladen_weight_kg",
        "kerb_weight": "unladen_weight_kg",
        "curb_weight": "unladen_weight_kg",
        "weight": "unladen_weight_kg",
        "gross_weight": "gross_weight_kg",
        "max._weight": "gross_weight_kg",
        
        # Cargo
        "cargo_volume": "cargo_volume_l",
        "trunk_volume": "cargo_volume_l",
        "boot_space": "cargo_volume_l",
        
        # Aerodynamics
        "drag_coefficient": "aerodynamics_cd",
        "cd": "aerodynamics_cd",
        "aerodynamic_drag_coefficient": "aerodynamics_cd",
        
        # Turning
        "turning_radius": "turning_circle_m",
        "turning_circle": "turning_circle_m",
        "turning_diameter": "turning_circle_m",
        
        # Fuel economy
        "fuel_consumption_(economy)_-_urban": "fuel_economy_city",
        "fuel_consumption_-_city": "fuel_economy_city",
        "city_fuel_consumption": "fuel_economy_city",
        "fuel_consumption_(economy)_-_extra_urban": "fuel_economy_highway",
        "fuel_consumption_-_highway": "fuel_economy_highway",
        "highway_fuel_consumption": "fuel_economy_highway",
        "fuel_consumption_(economy)_-_combined": "fuel_economy_combined",
        "fuel_consumption_-_combined": "fuel_economy_combined",
        "combined_fuel_consumption": "fuel_economy_combined",
        
        # Emissions
        "co2_emissions": "co2_emissions_g_km",
        "co2": "co2_emissions_g_km",
        "emissions": "co2_emissions_g_km",
    }

    # Separate extra data from main specs
    extra_data = {}
    
    for raw_key, raw_value in raw_specs.items():
        db_key = key_map.get(raw_key)
        if not db_key:
            # Store unmapped keys in extra field for future reference
            extra_data[raw_key] = raw_value
            continue

        # Skip if we already have this value (prefer first occurrence)
        if db_key in cleaned_specs:
            continue

        # Parse horsepower with optional RPM
        if db_key == "horsepower":
            cleaned_specs["horsepower"] = get_int(raw_value.split("@")[0])
            if "@" in raw_value:
                rpm_part = raw_value.split("@")[1]
                cleaned_specs["horsepower_rpm"] = get_int(rpm_part)
        
        # Parse torque with optional RPM range
        elif db_key == "torque":
            cleaned_specs["torque"] = get_int(raw_value.split("@")[0])
            if "@" in raw_value:
                rpm_part = raw_value.split("@")[1]
                rpms = [get_int(r) for r in rpm_part.split('-')]
                if len(rpms) == 1:
                    cleaned_specs["torque_rpm_min"] = rpms[0]
                elif len(rpms) > 1:
                    cleaned_specs["torque_rpm_min"] = rpms[0]
                    cleaned_specs["torque_rpm_max"] = rpms[1]

        # Integer fields
        elif db_key in ["displacement", "top_speed", "length_mm", "width_mm", "height_mm", 
                        "wheelbase_mm", "ground_clearance_mm", "unladen_weight_kg", 
                        "gross_weight_kg", "cargo_volume_l", "co2_emissions_g_km"]:
            cleaned_specs[db_key] = get_int(raw_value)
        
        # Float fields
        elif db_key in ["acceleration_0_100", "fuel_capacity", "aerodynamics_cd", 
                        "turning_circle_m", "fuel_economy_city", "fuel_economy_highway", 
                        "fuel_economy_combined"]:
            cleaned_specs[db_key] = get_float(raw_value)
        
        # String fields (transmission, drive_type, fuel_type, brake types, tire sizes)
        else:
            # For string fields, just use the value as-is (could be string or already processed)
            if isinstance(raw_value, str):
                cleaned_specs[db_key] = raw_value
            elif isinstance(raw_value, (int, float)):
                cleaned_specs[db_key] = str(raw_value)
            else:
                cleaned_specs[db_key] = raw_value
    
    # Add extra data if any unmapped keys were found
    if extra_data:
        cleaned_specs["extra"] = extra_data

    return cleaned_specs

