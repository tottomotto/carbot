"""Core scraping functions for AutoEvolution."""
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parents[2]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

import re
from db.models import Generation, Model, Spec, Version, Image
from scripts.autoevolution.config import logger, BASE_URL
from scripts.autoevolution.database import get_or_create
from scripts.autoevolution.spec_extractor import extract_all_specs, flatten_specs_for_db
from scripts.autoevolution.unit_parser import parse_specs_with_units


async def handle_cookie_consent(page):
    """Checks for and accepts the cookie consent banner using multiple selectors."""
    logger.info("Checking for cookie consent banner...")
    
    try:
        # Wait a moment for the banner to appear
        await page.wait_for_timeout(1000)
        
        selectors = [
            'button:has-text("AGREE")',              # Main consent dialog
            'button.fc-cta-consent',                 # Cookie banner
            'button:has-text("Accept")',
            'button:has-text("I Accept")',
            'button:has-text("I Agree")',
            '#onetrust-accept-btn-handler',
        ]
        
        for selector in selectors:
            try:
                btn = await page.query_selector(selector)
                if btn:
                    # Check if button is visible
                    is_visible = await btn.is_visible()
                    if is_visible:
                        logger.info(f"Cookie consent banner found with selector: '{selector}'. Clicking accept.")
                        await btn.click()
                        # Wait for banner to disappear and cookies to be saved
                        await page.wait_for_timeout(2000)
                        logger.info("Cookie consent accepted and preferences saved.")
                        return True
            except Exception as e:
                continue
        
        logger.info("No cookie consent banner found.")
    except Exception as e:
        logger.warning(f"Could not handle cookie consent: {e}")
    return False


async def fetch_generation_details(page, db, generation_obj):
    """Scrapes all versions and specs for a given generation."""
    logger.info(f"--- Fetching Versions for {generation_obj.gen_name} ---")
    await page.goto(generation_obj.url, wait_until="domcontentloaded")
    
    # Handle cookie consent after navigation
    await handle_cookie_consent(page)

    # The page structure uses anchor tags with IDs for each engine variant
    # Example: #aeng_bmw-ms-cs-2021-44l-v8-8at-635-hp
    # Each engine section follows the anchor
    
    # Find all engine sections - they're typically in divs after the anchor
    engine_sections = await page.query_selector_all('div.enginedata')
    if not engine_sections:
        logger.warning("No 'div.enginedata' found, trying alternative selectors...")
        engine_sections = await page.query_selector_all('table.techdata')
    
    logger.info(f"Found {len(engine_sections)} engine section(s)")
    
    for idx, section in enumerate(engine_sections):
        try:
            # Extract version name and anchor ID
            version_name = None
            anchor_id = None
            
            # Try to find the engine title - look for the preceding h2/h3 or the anchor
            # The structure is usually: <a id="aeng_..."></a><h2>Engine Name</h2><table>...</table>
            title_el = await section.evaluate('''(el) => {
                // Look backwards for h2/h3 or anchor
                let current = el.previousElementSibling;
                while (current) {
                    if (current.tagName === 'H2' || current.tagName === 'H3') {
                        return current.innerText;
                    }
                    if (current.tagName === 'A' && current.id && current.id.startsWith('aeng_')) {
                        // Found anchor, keep looking for title
                        if (!current.dataset.anchorId) {
                            current.dataset.anchorId = current.id;
                        }
                    }
                    current = current.previousElementSibling;
                }
                return null;
            }''')
            
            if title_el:
                version_name = title_el
            
            # Try to get the anchor ID
            anchor_id = await section.evaluate('''(el) => {
                let current = el.previousElementSibling;
                while (current) {
                    if (current.tagName === 'A' && current.id && current.id.startsWith('aeng_')) {
                        return current.id;
                    }
                    current = current.previousElementSibling;
                }
                return null;
            }''')
            
            if not version_name and anchor_id:
                # Extract readable name from ID
                version_name = anchor_id.replace('aeng_', '').replace('-', ' ').title()
            
            if not version_name:
                version_name = f"Version {idx + 1}"
                logger.warning(f"Could not extract version name, using: {version_name}")
            
            full_url = f"{generation_obj.url}#{anchor_id}" if anchor_id else generation_obj.url
            
            logger.debug(f"      - Version name: {version_name}, Anchor: {anchor_id}")

            version, v_created = get_or_create(
                db, Version,
                generation_id=generation_obj.id,
                version_name=version_name,
                defaults={"url": full_url}
            )
            if v_created:
                logger.info(f"    - Created Version: {version_name}")

            # Use comprehensive spec extraction
            all_specs = await extract_all_specs(page)
            
            # Flatten specs for database storage
            flat_specs, extra_data = flatten_specs_for_db(all_specs)
            
            if extra_data and "specs_with_units" in extra_data:
                # Parse specs with unit-specific columns
                cleaned_data = parse_specs_with_units(extra_data["specs_with_units"])
                
                # Add extra data (infotainment, features, etc.)
                cleaned_data["extra"] = {
                    "infotainment": extra_data.get("infotainment", []),
                    "highlight_features": extra_data.get("highlight_features", []),
                }
                
                # Store specs in database
                get_or_create(db, Spec, version_id=version.id, defaults=cleaned_data)
                logger.info(f"      - Stored {len(cleaned_data)} spec fields for {version_name}")
                
                # Store gallery images if available
                if "gallery_images" in extra_data:
                    for img_data in extra_data["gallery_images"][:10]:  # Limit to 10 images
                        get_or_create(
                            db, Image,
                            version_id=version.id,
                            url=img_data["url"],
                            defaults={"caption": img_data.get("caption", "")}
                        )
                    logger.info(f"      - Stored {len(extra_data['gallery_images'][:10])} images for {version_name}")
            else:
                logger.warning(f"      - No specs found for {version_name}")

        except Exception as e:
            logger.error(f"Could not parse engine section {idx}: {e}", exc_info=True)


async def fetch_model_details(page, db, brand_obj, model_name, model_url):
    """Scrapes all generations for a given model and inserts them into the DB."""
    logger.info(f"--- Fetching Generations for {model_name} ---")
    await page.goto(model_url, wait_until="domcontentloaded")
    
    # Handle cookie consent after navigation
    await handle_cookie_consent(page)
    
    model, _ = get_or_create(db, Model, brand_id=brand_obj.id, name=model_name.upper())

    # Find generation blocks on the page
    generation_elements = await page.query_selector_all("section.timeline-block")
    for element in generation_elements:
        try:
            name_el = await element.query_selector("h2 a")
            years_el = await element.query_selector("span.model-years")
            
            if name_el and years_el:
                gen_name = await name_el.inner_text()
                gen_url = BASE_URL + await name_el.get_attribute("href")
                years_text = await years_el.inner_text()
                
                # Extract start and end years
                match = re.search(r"(\d{4})-(\d{4}|present)", years_text)
                start_year, end_year = None, None
                if match:
                    start_year = int(match.group(1))
                    end_year = None if match.group(2) == 'present' else int(match.group(2))

                generation, created = get_or_create(
                    db, Generation,
                    model_id=model.id,
                    gen_name=gen_name,
                    defaults={
                        "url": gen_url,
                        "start_year": start_year,
                        "end_year": end_year
                    }
                )
                if created:
                    logger.info(f"  - Created Generation: {gen_name}")
                
                # Now, fetch the versions for this generation
                await fetch_generation_details(page, db, generation)

        except Exception as e:
            logger.warning(f"Could not parse a generation element for {model_name}: {e}")

