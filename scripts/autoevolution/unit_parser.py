"""
Unit-aware spec parser that extracts all available units from scraped data.

This module parses specs and populates unit-specific database columns for:
- Power (HP, kW, BHP)
- Torque (Nm, lb-ft)
- Fuel capacity (L, gal)
- Dimensions (mm, in)
- Weight (kg, lbs)
- Fuel economy (L/100km, mpg)
- Top speed (km/h, mph)
"""
import re


def parse_power_from_text(power_text):
    """
    Extract all power values from text.
    
    Example input: "467 KW @ 6000 RPM\n635 HP @ 6000 RPM\n626 BHP @ 6000 RPM"
    Returns: {"kw": 467, "hp": 635, "bhp": 626, "rpm": 6000}
    """
    result = {}
    
    if not power_text:
        return result
    
    # Extract kW
    kw_match = re.search(r'(\d+)\s*kw', power_text, re.I)
    if kw_match:
        result["kw"] = int(kw_match.group(1))
    
    # Extract HP (metric horsepower)
    hp_match = re.search(r'(\d+)\s*hp', power_text, re.I)
    if hp_match:
        result["hp"] = int(hp_match.group(1))
    
    # Extract BHP (brake horsepower)
    bhp_match = re.search(r'(\d+)\s*bhp', power_text, re.I)
    if bhp_match:
        result["bhp"] = int(bhp_match.group(1))
    
    # Extract RPM
    rpm_match = re.search(r'@\s*(\d+)\s*rpm', power_text, re.I)
    if rpm_match:
        result["rpm"] = int(rpm_match.group(1))
    
    return result


def parse_torque_from_text(torque_text):
    """
    Extract all torque values from text.
    
    Example input: "553 lb-ft @ 1800-5950 RPM\n750 Nm @ 1800-5950 RPM"
    Returns: {"lb_ft": 553, "nm": 750, "rpm_min": 1800, "rpm_max": 5950}
    """
    result = {}
    
    if not torque_text:
        return result
    
    # Extract lb-ft
    lbft_match = re.search(r'(\d+)\s*lb[- ]ft', torque_text, re.I)
    if lbft_match:
        result["lb_ft"] = int(lbft_match.group(1))
    
    # Extract Nm
    nm_match = re.search(r'(\d+)\s*nm', torque_text, re.I)
    if nm_match:
        result["nm"] = int(nm_match.group(1))
    
    # Extract RPM range
    rpm_match = re.search(r'@\s*(\d+)[-–](\d+)\s*rpm', torque_text, re.I)
    if rpm_match:
        result["rpm_min"] = int(rpm_match.group(1))
        result["rpm_max"] = int(rpm_match.group(2))
    elif re.search(r'@\s*(\d+)\s*rpm', torque_text, re.I):
        rpm = int(re.search(r'@\s*(\d+)\s*rpm', torque_text, re.I).group(1))
        result["rpm_min"] = rpm
        result["rpm_max"] = rpm
    
    return result


def parse_dimension_with_units(dimension_text):
    """
    Extract dimension in both mm and inches.
    
    Example input: "74.9 in (1902 mm)" or "196.9 in (5001 mm)"
    Returns: {"mm": 1902, "in": 74.9}
    """
    result = {}
    
    if not dimension_text:
        return result
    
    # Extract inches
    in_match = re.search(r'([\d\.]+)\s*in', str(dimension_text), re.I)
    if in_match:
        result["in"] = float(in_match.group(1))
    
    # Extract mm
    mm_match = re.search(r'(\d+)\s*mm', str(dimension_text), re.I)
    if mm_match:
        result["mm"] = int(mm_match.group(1))
    
    return result


def parse_fuel_economy(fuel_text):
    """
    Extract fuel economy in both L/100km and mpg.
    
    Example input: "13.9 mpg US (16.9 L/100Km)"
    Returns: {"mpg": 13.9, "l_100km": 16.9}
    """
    result = {}
    
    if not fuel_text:
        return result
    
    # Extract mpg
    mpg_match = re.search(r'([\d\.]+)\s*mpg', str(fuel_text), re.I)
    if mpg_match:
        result["mpg"] = float(mpg_match.group(1))
    
    # Extract L/100km
    l100_match = re.search(r'([\d\.]+)\s*l/100', str(fuel_text), re.I)
    if l100_match:
        result["l_100km"] = float(l100_match.group(1))
    
    return result


def parse_fuel_capacity(fuel_text):
    """
    Extract fuel capacity in liters and gallons.
    
    Example input: "18.5 gal (70 L)" or "70 L"
    Returns: {"l": 70, "gal": 18.5}
    """
    result = {}
    
    if not fuel_text:
        return result
    
    # Extract gallons
    gal_match = re.search(r'([\d\.]+)\s*gal', str(fuel_text), re.I)
    if gal_match:
        result["gal"] = float(gal_match.group(1))
    
    # Extract liters
    l_match = re.search(r'([\d\.]+)\s*l\b', str(fuel_text), re.I)
    if l_match:
        result["l"] = float(l_match.group(1))
    
    return result


def parse_weight(weight_text):
    """
    Extract weight in kg and lbs.
    
    Example input: "4023 lbs (1825 kg)" or "1825 kg"
    Returns: {"kg": 1825, "lbs": 4023}
    """
    result = {}
    
    if not weight_text:
        return result
    
    # Extract lbs
    lbs_match = re.search(r'(\d+)\s*lbs?', str(weight_text), re.I)
    if lbs_match:
        result["lbs"] = int(lbs_match.group(1))
    
    # Extract kg
    kg_match = re.search(r'(\d+)\s*kg', str(weight_text), re.I)
    if kg_match:
        result["kg"] = int(kg_match.group(1))
    
    return result


def parse_specs_with_units(specs_with_units):
    """
    Parse all specs and extract values for all unit-specific database columns.
    
    Args:
        specs_with_units: Dict from spec_extractor with {"key": {"value": X, "unit": Y}}
    
    Returns:
        dict: Cleaned data ready for database insertion with all unit columns
    """
    result = {}
    
    # Power - extract from the full power text
    if "power" in specs_with_units:
        power_data = specs_with_units["power"]
        if isinstance(power_data, dict) and "value" in power_data:
            power_text = str(power_data["value"])
            power_values = parse_power_from_text(power_text)
            if "kw" in power_values:
                result["power_kw"] = power_values["kw"]
            if "hp" in power_values:
                result["power_hp"] = power_values["hp"]
            if "bhp" in power_values:
                result["power_bhp"] = power_values["bhp"]
            if "rpm" in power_values:
                result["power_rpm"] = power_values["rpm"]
    
    # Torque - extract from the full torque text
    if "torque" in specs_with_units:
        torque_data = specs_with_units["torque"]
        if isinstance(torque_data, dict) and "value" in torque_data:
            torque_text = str(torque_data["value"])
            torque_values = parse_torque_from_text(torque_text)
            if "nm" in torque_values:
                result["torque_nm"] = torque_values["nm"]
            if "lb_ft" in torque_values:
                result["torque_lb_ft"] = torque_values["lb_ft"]
            if "rpm_min" in torque_values:
                result["torque_rpm_min"] = torque_values["rpm_min"]
            if "rpm_max" in torque_values:
                result["torque_rpm_max"] = torque_values["rpm_max"]
    
    # Dimensions - length, width, height, wheelbase
    for dim_name in ["length", "width", "height", "wheelbase"]:
        if dim_name in specs_with_units:
            dim_data = specs_with_units[dim_name]
            if isinstance(dim_data, dict):
                # Get the full text which might have both units
                dim_text = f"{dim_data.get('value', '')} {dim_data.get('unit', '')}"
                dim_values = parse_dimension_with_units(dim_text)
                if "mm" in dim_values:
                    result[f"{dim_name}_mm"] = dim_values["mm"]
                if "in" in dim_values:
                    result[f"{dim_name}_in"] = dim_values["in"]
    
    # Fuel capacity
    if "fuel_capacity" in specs_with_units or "fuel_tank_capacity" in specs_with_units:
        fuel_data = specs_with_units.get("fuel_capacity") or specs_with_units.get("fuel_tank_capacity")
        if isinstance(fuel_data, dict):
            fuel_text = f"{fuel_data.get('value', '')} {fuel_data.get('unit', '')}"
            fuel_values = parse_fuel_capacity(fuel_text)
            if "l" in fuel_values:
                result["fuel_capacity_l"] = fuel_values["l"]
            if "gal" in fuel_values:
                result["fuel_capacity_gal"] = fuel_values["gal"]
    
    # Fuel economy - city, highway, combined
    for eco_type in ["city", "highway", "combined"]:
        key = f"fuel_consumption_-_{eco_type}"
        alt_key = f"{eco_type}_fuel_consumption"
        
        if key in specs_with_units or alt_key in specs_with_units:
            eco_data = specs_with_units.get(key) or specs_with_units.get(alt_key)
            if isinstance(eco_data, dict):
                eco_text = f"{eco_data.get('value', '')} {eco_data.get('unit', '')}"
                eco_values = parse_fuel_economy(eco_text)
                if "mpg" in eco_values:
                    result[f"fuel_economy_{eco_type}_mpg"] = eco_values["mpg"]
                if "l_100km" in eco_values:
                    result[f"fuel_economy_{eco_type}_l_100km"] = eco_values["l_100km"]
    
    # Weight - unladen (curb) and gross
    for weight_type in ["unladen_weight", "kerb_weight", "curb_weight", "weight"]:
        if weight_type in specs_with_units:
            weight_data = specs_with_units[weight_type]
            if isinstance(weight_data, dict):
                weight_text = f"{weight_data.get('value', '')} {weight_data.get('unit', '')}"
                weight_values = parse_weight(weight_text)
                if "kg" in weight_values:
                    result["unladen_weight_kg"] = weight_values["kg"]
                if "lbs" in weight_values:
                    result["unladen_weight_lbs"] = weight_values["lbs"]
            break  # Use first found
    
    # Displacement
    if "displacement" in specs_with_units:
        disp_data = specs_with_units["displacement"]
        if isinstance(disp_data, dict) and "value" in disp_data:
            # AutoEvolution usually gives cc
            result["displacement_cc"] = int(disp_data["value"]) if isinstance(disp_data["value"], (int, float)) else None
            if result["displacement_cc"]:
                result["displacement_l"] = round(result["displacement_cc"] / 1000, 1)
    
    # Cylinders
    if "cylinders" in specs_with_units:
        cyl_data = specs_with_units["cylinders"]
        if isinstance(cyl_data, dict) and "value" in cyl_data:
            result["cylinders"] = str(cyl_data["value"])
    
    # Fuel type
    if "fuel" in specs_with_units:
        fuel_data = specs_with_units["fuel"]
        if isinstance(fuel_data, dict) and "value" in fuel_data:
            result["fuel_type"] = str(fuel_data["value"])
    
    # Transmission
    if "gearbox" in specs_with_units or "transmission" in specs_with_units:
        trans_data = specs_with_units.get("gearbox") or specs_with_units.get("transmission")
        if isinstance(trans_data, dict):
            trans_text = f"{trans_data.get('value', '')} {trans_data.get('unit', '')}"
            result["transmission"] = trans_text.strip()
    
    # Drive type
    if "drive_type" in specs_with_units or "drive_train" in specs_with_units:
        drive_data = specs_with_units.get("drive_type") or specs_with_units.get("drive_train")
        if isinstance(drive_data, dict) and "value" in drive_data:
            result["drive_type"] = str(drive_data["value"])
    
    # Brakes
    if "front" in specs_with_units:  # Front brakes
        brake_data = specs_with_units["front"]
        if isinstance(brake_data, dict) and "value" in brake_data:
            result["brake_type_front"] = str(brake_data["value"])
    
    if "rear" in specs_with_units:  # Rear brakes
        brake_data = specs_with_units["rear"]
        if isinstance(brake_data, dict) and "value" in brake_data:
            result["brake_type_rear"] = str(brake_data["value"])
    
    # Top speed
    if "top_speed" in specs_with_units or "maximum_speed" in specs_with_units:
        speed_data = specs_with_units.get("top_speed") or specs_with_units.get("maximum_speed")
        if isinstance(speed_data, dict) and "value" in speed_data:
            # Assume km/h by default from AutoEvolution
            speed_kph = int(speed_data["value"]) if isinstance(speed_data["value"], (int, float)) else None
            if speed_kph:
                result["top_speed_kph"] = speed_kph
                result["top_speed_mph"] = int(speed_kph * 0.621371)
    
    # Acceleration
    if "acceleration_0-62_mph_0-100_kph" in specs_with_units:
        acc_data = specs_with_units["acceleration_0-62_mph_0-100_kph"]
        if isinstance(acc_data, dict) and "value" in acc_data:
            acc_value = float(acc_data["value"]) if isinstance(acc_data["value"], (int, float)) else None
            if acc_value:
                result["acceleration_0_100_kph"] = acc_value
                # 0-60 mph is roughly the same as 0-100 km/h for practical purposes
                result["acceleration_0_60_mph"] = acc_value
    
    return result

