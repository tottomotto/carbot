"""Comprehensive spec extraction for AutoEvolution pages.

This module handles extraction of all visible specs including:
- Infotainment features (Apple CarPlay, Android Auto, etc.)
- Segmented spec tables (engine, performance, dimensions, brakes, fuel economy)
- Highlight features and bullet points
- Gallery images
- Values with units preserved (e.g., {"value": 635, "unit": "hp"})
"""
import sys
from pathlib import Path
import re

# Add project root to path
project_root = Path(__file__).resolve().parents[2]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from scripts.autoevolution.config import logger


def extract_value_and_unit(raw_string):
    """
    Splits a spec string into value and unit.
    
    Examples:
        "635 hp" -> {"value": 635, "unit": "hp"}
        "4983 mm" -> {"value": 4983, "unit": "mm"}
        "3.0 sec" -> {"value": 3.0, "unit": "sec"}
        "Petrol" -> {"value": "Petrol", "unit": None}
    
    Returns:
        dict: {"value": <number or string>, "unit": <string or None>}
    """
    if not raw_string:
        return {"value": None, "unit": None}
    
    raw_string = raw_string.strip()
    
    # Try to match number(s) followed by optional unit
    # Handles: "635 hp", "4,983 mm", "3.0 sec", "750 Nm @ 1,800-5,860 rpm"
    match = re.match(r"^\s*([\d\.,]+)\s*([^\d\s].*)?$", raw_string)
    
    if match:
        # Extract numeric value
        val_str = match.group(1).replace(",", "")
        
        # Try to parse as float or int
        try:
            if "." in val_str:
                value = float(val_str)
            else:
                value = int(val_str)
        except ValueError:
            # If parsing fails, keep as string
            value = val_str
        
        # Extract unit (everything after the number)
        unit = match.group(2).strip() if match.group(2) else None
        
        # Clean up common unit patterns
        if unit:
            # Remove extra info like "@ 6,000 rpm" from units
            unit = unit.split("@")[0].strip()
            # Remove trailing punctuation
            unit = unit.rstrip(".,;:")
        
        return {"value": value, "unit": unit}
    
    # If no number found, treat entire string as a text value
    return {"value": raw_string, "unit": None}


async def extract_infotainment_features(page):
    """Extract infotainment and connectivity features from icons/badges."""
    infotainment_icons = []
    
    # Find any icons/buttons with 'CarPlay' or 'Android' or other connectivity features
    selectors = [
        "img[alt*='CarPlay' i]",
        "img[alt*='Android Auto' i]",
        "img[alt*='Bluetooth' i]",
        ".infotainment-icon",
        "[data-feature*='carplay' i]",
        "[data-feature*='android' i]"
    ]
    
    for selector in selectors:
        try:
            elements = await page.query_selector_all(selector)
            for el in elements:
                alt = await el.get_attribute("alt")
                title = await el.get_attribute("title")
                src = await el.get_attribute("src")
                data_feature = await el.get_attribute("data-feature")
                
                # Normalize icon detection
                label = (alt or title or data_feature or "").lower()
                if label and label not in infotainment_icons:
                    infotainment_icons.append(label)
                elif src and "carplay" in src.lower() or "android" in src.lower():
                    infotainment_icons.append(src.split("/")[-1].replace(".png", "").replace(".jpg", ""))
        except Exception as e:
            logger.debug(f"Error extracting infotainment from selector '{selector}': {e}")
            continue
    
    return infotainment_icons


async def extract_spec_tables(page):
    """Extract all spec tables/blocks organized by category."""
    all_specs = {}
    
    # Look for all tables or blocks with spec details
    spec_blocks = await page.query_selector_all(
        "table.techdata, table.specs, .specs-block, .engine-data, .car-specs, .performance-specs, div.enginedata"
    )
    
    logger.debug(f"Found {len(spec_blocks)} spec blocks")
    
    for idx, block in enumerate(spec_blocks):
        try:
            # Detect block title/category if present
            category_title = None
            
            # Try finding header directly above table
            try:
                category_title = await block.evaluate('''(el) => {
                    let prev = el.previousElementSibling;
                    while (prev) {
                        if (prev.tagName === 'H2' || prev.tagName === 'H3' || prev.tagName === 'H4') {
                            return prev.textContent;
                        }
                        prev = prev.previousElementSibling;
                    }
                    return null;
                }''')
            except Exception as e:
                logger.debug(f"Could not extract category title for block {idx}: {e}")
            
            category = (category_title or "").strip().lower().replace(" ", "_") if category_title else f"block_{idx}"
            
            specs = {}
            
            # Parse all key-value rows
            rows = await block.query_selector_all("tr")
            for row in rows:
                try:
                    cells = await row.query_selector_all("td, th")
                    if len(cells) >= 2:
                        key_text = await cells[0].inner_text()
                        value_text = await cells[1].inner_text()
                        
                        if key_text and value_text:
                            # Clean the key
                            key = key_text.strip().lower().replace(" ", "_").replace(":", "").replace("(", "").replace(")", "").rstrip("_")
                            # Extract value and unit
                            specs[key] = extract_value_and_unit(value_text.strip())
                except Exception as e:
                    logger.debug(f"Error parsing row in block {idx}: {e}")
                    continue
            
            if specs:
                # Use block header/title as category, or generic name
                all_specs[category] = specs
                logger.debug(f"Extracted {len(specs)} specs from category '{category}'")
        
        except Exception as e:
            logger.warning(f"Error processing spec block {idx}: {e}")
            continue
    
    return all_specs


async def extract_highlight_features(page):
    """Extract unstructured highlight features from paragraphs and bullet points."""
    features = []
    
    # Search for features in common containers
    selectors = [
        "div.infotainment",
        "ul.features",
        ".highlight-features",
        ".key-features",
        "div.features-list",
        "ul.equipment"
    ]
    
    for selector in selectors:
        try:
            highlight_block = await page.query_selector(selector)
            if highlight_block:
                # Extract list items
                items = await highlight_block.query_selector_all("li")
                for li in items:
                    text = await li.inner_text()
                    if text and text.strip():
                        features.append(text.strip())
                
                # Also check for paragraphs if no list items
                if not items:
                    paragraphs = await highlight_block.query_selector_all("p")
                    for p in paragraphs:
                        text = await p.inner_text()
                        if text and text.strip():
                            features.append(text.strip())
        except Exception as e:
            logger.debug(f"Error extracting features from '{selector}': {e}")
            continue
    
    return features


async def extract_gallery_images(page):
    """Extract gallery/spec images from the page."""
    gallery = []
    
    # Look for images in common gallery containers
    selectors = [
        "img.gallery",
        ".spec-image img",
        ".car-gallery img",
        "img[alt*='bmw' i]",
        ".photo-gallery img",
        "div.images img"
    ]
    
    for selector in selectors:
        try:
            images = await page.query_selector_all(selector)
            for img in images:
                src = await img.get_attribute("src")
                alt = await img.get_attribute("alt")
                
                if src and src not in gallery:
                    # Filter out small icons and placeholders
                    if "icon" not in src.lower() and "placeholder" not in src.lower():
                        gallery.append({
                            "url": src if src.startswith("http") else f"https://www.autoevolution.com{src}",
                            "caption": alt or ""
                        })
        except Exception as e:
            logger.debug(f"Error extracting images from '{selector}': {e}")
            continue
    
    return gallery


async def extract_all_specs(page):
    """
    Extract all visible specs from the page including:
    - Infotainment features (CarPlay, Android Auto, etc.)
    - Spec tables organized by category
    - Highlight features and bullet points
    - Gallery images
    
    Returns:
        dict: Comprehensive spec data organized by category
    """
    logger.info("Extracting comprehensive specs from page...")
    
    all_data = {}
    
    # Extract infotainment features
    try:
        infotainment = await extract_infotainment_features(page)
        if infotainment:
            all_data["infotainment"] = infotainment
            logger.debug(f"Found {len(infotainment)} infotainment features")
    except Exception as e:
        logger.warning(f"Error extracting infotainment features: {e}")
    
    # Extract spec tables
    try:
        spec_tables = await extract_spec_tables(page)
        if spec_tables:
            all_data["specs"] = spec_tables
            logger.debug(f"Found {len(spec_tables)} spec categories")
    except Exception as e:
        logger.warning(f"Error extracting spec tables: {e}")
    
    # Extract highlight features
    try:
        features = await extract_highlight_features(page)
        if features:
            all_data["highlight_features"] = features
            logger.debug(f"Found {len(features)} highlight features")
    except Exception as e:
        logger.warning(f"Error extracting highlight features: {e}")
    
    # Extract gallery images
    try:
        gallery = await extract_gallery_images(page)
        if gallery:
            all_data["gallery_images"] = gallery
            logger.debug(f"Found {len(gallery)} gallery images")
    except Exception as e:
        logger.warning(f"Error extracting gallery images: {e}")
    
    logger.info(f"Extracted {len(all_data)} data categories from page")
    return all_data


def flatten_specs_for_db(all_specs):
    """
    Flatten the comprehensive spec data into a format suitable for the database.
    
    The function now handles specs with units:
    - Extracts numeric values for database columns
    - Preserves full value+unit data in extra_data for reference
    
    Returns:
        tuple: (flat_specs_dict, extra_data_dict)
            - flat_specs_dict: Specs with just values (for parsing into DB columns)
            - extra_data_dict: Full data including units, infotainment, features, images
    """
    flat_specs = {}
    extra_data = {}
    
    # Store the complete specs with units for reference
    specs_with_units = {}
    
    # Extract the main spec tables
    if "specs" in all_specs:
        for category, specs in all_specs["specs"].items():
            # For each spec, extract the value for DB columns
            # and preserve the full value+unit structure
            for key, value_unit_dict in specs.items():
                # Extract just the value for parsing
                flat_specs[key] = value_unit_dict.get("value")
                
                # Store the complete value+unit structure
                if key not in specs_with_units:
                    specs_with_units[key] = value_unit_dict
    
    # Store specs with units in extra data
    if specs_with_units:
        extra_data["specs_with_units"] = specs_with_units
    
    # Store non-spec data in extra
    if "infotainment" in all_specs:
        extra_data["infotainment"] = all_specs["infotainment"]
    
    if "highlight_features" in all_specs:
        extra_data["highlight_features"] = all_specs["highlight_features"]
    
    if "gallery_images" in all_specs:
        extra_data["gallery_images"] = all_specs["gallery_images"]
    
    return flat_specs, extra_data

