"""Main entry point for AutoEvolution scraper."""
import asyncio
import argparse
import sys
from pathlib import Path
import re
import os

# --- Project Setup ---
# Add project root to the Python path
project_root = Path(__file__).resolve().parents[2]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from playwright.async_api import async_playwright
from db import SessionLocal
from db.models import Brand, Model, Generation
from scripts.autoevolution.config import logger, BASE_URL
from scripts.autoevolution.database import get_or_create
from scripts.autoevolution.scraper import handle_cookie_consent, fetch_model_details, fetch_generation_details

# Path for storing cookies/session state
STORAGE_STATE_PATH = project_root / "scripts" / "autoevolution" / "cookies.json"


async def main(brand_slug=None, model_slug=None, generation_url=None):
    """The main entry point for the scraper."""
    db = SessionLocal()
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        
        # Load cookies if they exist, otherwise start fresh
        context_options = {}
        if STORAGE_STATE_PATH.exists():
            logger.info(f"Loading saved cookies from {STORAGE_STATE_PATH}")
            context_options["storage_state"] = str(STORAGE_STATE_PATH)
        
        context = await browser.new_context(**context_options)
        page = await context.new_page()

        try:
            if brand_slug:
                logger.info(f"Processing brand: {brand_slug}")
                brand, _ = get_or_create(db, Brand, name=brand_slug.upper())
                
                if model_slug:
                    logger.info(f"Processing model: {model_slug}")
                    model_url = f"{BASE_URL}/{brand_slug}/{model_slug}/"
                    await fetch_model_details(page, db, brand, model_slug, model_url)
            
            elif generation_url:
                logger.info(f"Processing single generation URL: {generation_url}")
                await page.goto(generation_url, wait_until="domcontentloaded")
                
                # Handle cookie consent on first page load
                await handle_cookie_consent(page)
                
                title = await page.title()
                match = re.search(r"^(.*?)\s(.*?)\s\((.*?)\)", title)
                if not match:
                    logger.error(f"Could not parse brand, model, and generation from title: '{title}'")
                    return
                
                brand_name, model_name, gen_name = match.groups()

                logger.info(f"Inferred Brand: {brand_name}, Model: {model_name}, Generation: {gen_name}")

                brand, _ = get_or_create(db, Brand, name=brand_name.upper())
                model, _ = get_or_create(db, Model, brand_id=brand.id, name=model_name.upper())

                gen, created = get_or_create(
                    db, Generation,
                    model_id=model.id,
                    gen_name=gen_name,
                    defaults={"url": generation_url}
                )
                if created:
                    logger.info(f"Created Generation: {gen_name}")
                
                await fetch_generation_details(page, db, gen)

            db.commit()
            
            # Save cookies/session state for future runs
            await context.storage_state(path=str(STORAGE_STATE_PATH))
            logger.info(f"Saved cookies to {STORAGE_STATE_PATH}")

        except Exception as e:
            logger.error(f"An error occurred: {e}", exc_info=True)
            db.rollback()
        finally:
            await browser.close()
            db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Scrape car specs from AutoEvolution.")
    parser.add_argument('--brand', type=str, help="Brand slug (e.g. bmw)")
    parser.add_argument('--model', type=str, help="Model slug (e.g. m5)")
    parser.add_argument('--generation_url', type=str, help="Full generation URL to scrape directly.")
    args = parser.parse_args()

    if not any([args.brand, args.generation_url]):
        logger.error("You must provide a --brand or a --generation_url to start scraping.")
    else:
        asyncio.run(main(
            brand_slug=args.brand,
            model_slug=args.model,
            generation_url=args.generation_url
        ))

