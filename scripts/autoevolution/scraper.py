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


async def handle_cookie_consent(page, cookies_loaded=False):
    """Checks for and accepts the cookie consent banner using multiple selectors.
    
    Args:
        page: Playwright page object
        cookies_loaded: If True, skips waiting and only checks quickly for consent banner
    """
    if cookies_loaded:
        logger.info("Cookies loaded from file, skipping consent wait...")
        # Do a quick check without waiting - consent banner shouldn't appear
        try:
            selectors = [
                'button:has-text("AGREE")',
                'button.fc-cta-consent',
                'button:has-text("Accept")',
                'button:has-text("I Accept")',
                'button:has-text("I Agree")',
                '#onetrust-accept-btn-handler',
            ]
            
            for selector in selectors:
                btn = await page.query_selector(selector)
                if btn and await btn.is_visible():
                    logger.warning("Unexpected cookie banner appeared despite loaded cookies. Accepting...")
                    await btn.click()
                    await page.wait_for_timeout(1000)
                    return True
            
            logger.info("No cookie consent banner detected (as expected).")
            return False
        except Exception as e:
            logger.debug(f"Quick cookie check error (can ignore): {e}")
            return False
    
    # No cookies loaded - wait for and handle consent banner
    logger.info("No cookies loaded, checking for cookie consent banner...")
    
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


async def fetch_generation_details(page, db, generation_obj, cookies_loaded=False):
    """Scrapes all versions and specs for a given generation."""
    logger.info(f"      ╔{'═'*70}╗")
    logger.info(f"      ║ 🔧 FETCHING VERSION DETAILS: {generation_obj.gen_name:<48} ║")
    logger.info(f"      ╚{'═'*70}╝")
    logger.info(f"      📍 Navigating to: {generation_obj.url}")
    
    await page.goto(generation_obj.url, wait_until="domcontentloaded")
    logger.info(f"      ✓ Page loaded: {page.url}")
    
    # Handle cookie consent after navigation
    await handle_cookie_consent(page, cookies_loaded=cookies_loaded)

    # The page structure uses anchor tags with IDs for each engine variant
    # Example: #aeng_bmw-ms-cs-2021-44l-v8-8at-635-hp
    # Each engine section follows the anchor
    
    # Find all engine sections - they're typically in divs after the anchor
    logger.debug(f"      🔍 Looking for engine sections...")
    engine_sections = await page.query_selector_all('div.enginedata')
    if not engine_sections:
        logger.warning("      ⚠️  No 'div.enginedata' found, trying alternative selectors...")
        engine_sections = await page.query_selector_all('table.techdata')
    
    if not engine_sections:
        logger.error(f"      ✗ No engine sections found on page!")
        return
    
    logger.info(f"      ✓ Found {len(engine_sections)} engine section(s)")
    
    for idx, section in enumerate(engine_sections, 1):
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
                version_name = f"Version {idx}"
                logger.warning(f"         ⚠️  Could not extract version name, using: {version_name}")
            
            full_url = f"{generation_obj.url}#{anchor_id}" if anchor_id else generation_obj.url
            
            logger.info(f"\n         ┌{'─'*60}┐")
            logger.info(f"         │ 🏎️  [{idx}/{len(engine_sections)}] Version: {version_name:<44} │")
            logger.info(f"         └{'─'*60}┘")
            logger.debug(f"            Anchor ID: {anchor_id or 'N/A'}")
            logger.debug(f"            Full URL: {full_url}")

            version, v_created = get_or_create(
                db, Version,
                generation_id=generation_obj.id,
                version_name=version_name,
                defaults={"url": full_url}
            )
            if v_created:
                logger.info(f"            ✓ Created Version in DB: {version_name}")
            else:
                logger.info(f"            → Version already exists in DB: {version_name}")

            # Use comprehensive spec extraction
            logger.info(f"            🔍 Extracting specs from page...")
            all_specs = await extract_all_specs(page)
            logger.debug(f"            Found {len(all_specs.get('specs', {}))} raw spec entries")
            
            # Flatten specs for database storage
            flat_specs, extra_data = flatten_specs_for_db(all_specs)
            
            if extra_data and "specs_with_units" in extra_data:
                # Parse specs with unit-specific columns
                logger.debug(f"            📊 Parsing specs with units...")
                cleaned_data = parse_specs_with_units(extra_data["specs_with_units"])
                
                # Add extra data (infotainment, features, etc.)
                cleaned_data["extra"] = {
                    "infotainment": extra_data.get("infotainment", []),
                    "highlight_features": extra_data.get("highlight_features", []),
                }
                
                # Log some key specs if available
                if cleaned_data.get("horsepower_hp"):
                    logger.info(f"            💪 Power: {cleaned_data['horsepower_hp']} HP")
                if cleaned_data.get("torque_nm"):
                    logger.info(f"            🔧 Torque: {cleaned_data['torque_nm']} Nm")
                if cleaned_data.get("top_speed_kph"):
                    logger.info(f"            🏁 Top Speed: {cleaned_data['top_speed_kph']} km/h")
                
                # Store specs in database
                get_or_create(db, Spec, version_id=version.id, defaults=cleaned_data)
                logger.info(f"            ✓ Stored {len(cleaned_data)} spec fields for {version_name}")
                
                # Store gallery images if available
                if "gallery_images" in extra_data:
                    image_count = len(extra_data["gallery_images"][:10])
                    for img_data in extra_data["gallery_images"][:10]:  # Limit to 10 images
                        get_or_create(
                            db, Image,
                            version_id=version.id,
                            url=img_data["url"],
                            defaults={"caption": img_data.get("caption", "")}
                        )
                    logger.info(f"            📷 Stored {image_count} images for {version_name}")
                else:
                    logger.debug(f"            No gallery images found")
            else:
                logger.warning(f"            ⚠️  No specs found for {version_name}")

        except Exception as e:
            logger.error(f"         ✗ ERROR parsing engine section {idx}: {e}", exc_info=True)


async def get_generation_links(page, brand_slug):
    """Extract all generation links from a model overview page.
    
    Simple approach: Look for div.carmodel elements containing generation links.
    """
    logger.info("🔍 Scanning page for generation links...")
    
    # Wait for the carmodel divs to load
    try:
        await page.wait_for_selector("div.carmodel", timeout=5000)
        logger.debug("✓ Found div.carmodel elements")
    except Exception as e:
        logger.warning(f"⚠️  No div.carmodel elements found (timeout): {e}")
        logger.info("   Trying to continue anyway...")

    generation_links = []
    
    # Simple and direct: select all links inside carmodel divs
    # Structure: <div class="carmodel"><h2><a href="...">Generation Name</a></h2></div>
    logger.debug("Looking for generation links in div.carmodel h2 a...")
    gen_link_elements = await page.query_selector_all('div.carmodel h2 a')
    
    logger.info(f"Found {len(gen_link_elements)} generation link(s) in carmodel divs")
    
    for idx, link_el in enumerate(gen_link_elements, 1):
        try:
            url = await link_el.get_attribute('href')
            text = await link_el.inner_text()
            
            if not url or not text:
                logger.debug(f"  ✗ Skipping link {idx}: missing URL or text")
                continue
            
            text = text.strip()
            
            # Convert relative URLs to absolute
            if url.startswith("/"):
                full_url = f"{BASE_URL}{url}"
            elif url.startswith("http"):
                full_url = url
            else:
                full_url = f"{BASE_URL}/{url}"
            
            generation_links.append({
                "name": text,
                "url": full_url
            })
            
            logger.info(f"  → [{idx}] {text}")
            logger.debug(f"       URL: {full_url}")
                    
        except Exception as e:
            logger.warning(f"  ✗ Error extracting link {idx}: {e}")
            continue

    logger.info(f"✓ Extracted {len(generation_links)} generation link(s)")
    return generation_links


async def fetch_model_details(page, db, brand_obj, model_name, model_url, cookies_loaded=False):
    """Scrapes all generations for a given model and inserts them into the DB."""
    logger.info(f"\n{'='*80}")
    logger.info(f"🚗 FETCHING MODEL: {model_name} (Brand: {brand_obj.name})")
    logger.info(f"{'='*80}")
    logger.info(f"📍 Navigating to: {model_url}")
    
    await page.goto(model_url, wait_until="domcontentloaded")
    logger.info(f"✓ Page loaded: {page.url}")
    
    # Handle cookie consent after navigation
    await handle_cookie_consent(page, cookies_loaded=cookies_loaded)
    
    # Get or create model in database
    model, model_created = get_or_create(db, Model, brand_id=brand_obj.id, name=model_name.upper())
    if model_created:
        logger.info(f"✓ Created new model in DB: {model_name}")
    else:
        logger.info(f"→ Model already exists in DB: {model_name}")

    # Extract brand slug from URL for filtering
    brand_slug = brand_obj.name.lower().replace(" ", "-")
    logger.debug(f"Using brand slug for filtering: '{brand_slug}'")
    
    # Get all generation links from the page
    generation_links = await get_generation_links(page, brand_slug)
    
    if not generation_links:
        logger.warning(f"⚠️  No generations found for {model_name} at {model_url}")
        logger.warning(f"   This could mean:")
        logger.warning(f"   1. The page structure has changed")
        logger.warning(f"   2. The brand slug '{brand_slug}' doesn't match the URL pattern")
        logger.warning(f"   3. The page didn't load properly")
        return
    
    logger.info(f"\n📋 Processing {len(generation_links)} generation(s)...")
    
    # Process all generations
    for idx, gen_data in enumerate(generation_links, 1):
        try:
            gen_name = gen_data["name"]
            gen_url = gen_data["url"]
            
            logger.info(f"\n{'─'*80}")
            logger.info(f"📅 [{idx}/{len(generation_links)}] Processing Generation: {gen_name}")
            logger.info(f"🔗 URL: {gen_url}")
            
            # Extract years from the generation name if present
            # Example: "BMW M5 (F90) 2018-present" or "BMW M5 (E60) 2005-2010"
            start_year, end_year = None, None
            year_match = re.search(r"(\d{4})-(\d{4}|present)", gen_name)
            if year_match:
                start_year = int(year_match.group(1))
                end_year = None if year_match.group(2) == 'present' else int(year_match.group(2))
                logger.debug(f"   Extracted years: {start_year} - {end_year or 'present'}")

            generation, gen_created = get_or_create(
                db, Generation,
                model_id=model.id,
                gen_name=gen_name,
                defaults={
                    "url": gen_url,
                    "start_year": start_year,
                    "end_year": end_year
                }
            )
            if gen_created:
                logger.info(f"   ✓ Created Generation in DB: {gen_name}")
            else:
                logger.info(f"   → Generation already exists in DB: {gen_name}")
            
            # Now, fetch the versions for this generation
            logger.info(f"   🔄 Fetching version details for {gen_name}...")
            await fetch_generation_details(page, db, generation, cookies_loaded=cookies_loaded)
            logger.info(f"   ✓ Completed processing {gen_name}")

        except Exception as e:
            logger.error(f"   ✗ ERROR processing generation {gen_data.get('name', 'unknown')}: {e}", exc_info=True)
            continue
    
    logger.info(f"\n{'='*80}")
    logger.info(f"✓ COMPLETED MODEL: {model_name}")
    logger.info(f"{'='*80}\n")

