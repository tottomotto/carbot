"""Main entry point for AutoEvolution scraper."""
import asyncio
import argparse
import sys
from pathlib import Path
import re
import os
import time

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
    logger.info("\n" + "="*100)
    logger.info("🚀 AUTOEVOLUTION SCRAPER STARTED")
    logger.info("="*100)
    
    db = SessionLocal()
    async with async_playwright() as p:
        logger.info("🌐 Launching browser...")
        browser = await p.chromium.launch(headless=False)
        logger.info("✓ Browser launched successfully")
        
        # Load cookies if they exist, otherwise start fresh
        context_options = {}
        cookies_loaded = False
        if STORAGE_STATE_PATH.exists():
            logger.info(f"🍪 Loading saved cookies from {STORAGE_STATE_PATH}")
            context_options["storage_state"] = str(STORAGE_STATE_PATH)
            cookies_loaded = True
        else:
            logger.info("🍪 No saved cookies found, will handle consent on first page")
        
        context = await browser.new_context(**context_options)
        
        # Block ad and tracking requests at the browser level
        ad_domains = [
            'doubleclick.net', 'googlesyndication.com', 'google.com/recaptcha',
            'lijit.com', 'rubiconproject.com', 'crwdcntrl.net', 'pubmatic.com',
            'bidberry.net', 'adtrafficquality.google', 'safeframe', 'casalemedia.com',
            'adsrvr.org', 'advertising.com', 'adnxs.com', 'quantserve.com',
            'googletagmanager.com', 'googletagservices.com', 'google-analytics.com',
            'scorecardresearch.com', 'amazon-adsystem.com', 'ads-twitter.com',
            'facebook.net', 'outbrain.com', 'taboola.com', 'criteo.com',
            'tappx.com', 'indexww.com', 'snigelweb.com', 'clearnview.com'
        ]
        
        async def block_ads(route):
            """Block ads and tracking scripts."""
            if any(domain in route.request.url for domain in ad_domains):
                # Only log blocked document requests (not all resources)
                if route.request.resource_type == "document":
                    logger.info(f"🚫 Blocked document: {route.request.url}")
                else:
                    logger.debug(f"🚫 Blocked resource: {route.request.url}")
                await route.abort()
            else:
                await route.continue_()
        
        # Apply ad blocking to all requests
        await context.route("**/*", block_ads)
        logger.info(f"🛡️  Ad blocking enabled ({len(ad_domains)} domains blocked)")
        
        page = await context.new_page()
        
        # Comprehensive activity tracking
        activity_log = {
            "document_requests": 0,
            "all_requests": 0,
            "main_frame_navs": 0,
            "iframe_navs": 0,
            "page_loads": 0,
            "last_activity_time": None
        }
        
        def log_activity(event_type, details=""):
            activity_log["last_activity_time"] = time.time()
            timestamp = time.strftime("%H:%M:%S", time.localtime())
            logger.info(f"[{timestamp}] {event_type} {details}")
        
        def on_request(request):
            activity_log["all_requests"] += 1
            
            # Log only MAIN FRAME document requests
            if request.resource_type == "document":
                activity_log["document_requests"] += 1
                is_main_frame = request.frame == page.main_frame
                if is_main_frame:
                    log_activity(f"🌐 [Navigation #{activity_log['document_requests']}]", 
                               f"{request.method} → {request.url}")
        
        def on_response(response):
            if response.request.resource_type == "document":
                is_main_frame = response.request.frame == page.main_frame
                if is_main_frame:
                    log_activity(f"   ↳ Response", f"{response.status} {response.status_text}")
        
        def on_frame_navigated(frame):
            if frame == page.main_frame:
                activity_log["main_frame_navs"] += 1
                # Don't log frame navigation separately, it's redundant with request logging
                logger.debug(f"Main frame navigated: {frame.url}")
            else:
                activity_log["iframe_navs"] += 1
                # Log iframes at debug level only
                logger.debug(f"Iframe navigation: {frame.url}")
        
        def on_page_load():
            activity_log["page_loads"] += 1
            log_activity(f"✓ Page loaded", page.url)
        
        # Subscribe to ALL activity
        page.on("request", on_request)
        page.on("response", on_response)
        page.on("load", on_page_load)
        page.on("framenavigated", on_frame_navigated)
        page.on("close", lambda: log_activity("❌ Page closed event", ""))
        
        # Track context-level page creation
        context.on("page", lambda p: log_activity("🆕 New page created", p.url))
        
        logger.info("✓ Browser context created")
        logger.info("✓ Navigation tracking enabled (main frame only)\n")

        try:
            if brand_slug:
                logger.info(f"📋 MODE: Brand/Model scraping")
                logger.info(f"   Brand: {brand_slug}")
                brand, brand_created = get_or_create(db, Brand, name=brand_slug.upper())
                if brand_created:
                    logger.info(f"   ✓ Created brand in DB: {brand_slug.upper()}")
                else:
                    logger.info(f"   → Brand already exists: {brand_slug.upper()}")
                
                if model_slug:
                    logger.info(f"   Model: {model_slug}")
                    model_url = f"{BASE_URL}/{brand_slug}/{model_slug}/"
                    await fetch_model_details(page, db, brand, model_slug, model_url, cookies_loaded=cookies_loaded)
                else:
                    logger.warning("⚠️  No model specified, skipping...")
            
            elif generation_url:
                logger.info(f"📋 MODE: Direct generation URL scraping")
                logger.info(f"   URL: {generation_url}")
                logger.info(f"📍 Navigating to generation page...")
                
                await page.goto(generation_url, wait_until="domcontentloaded")
                logger.info(f"✓ Page loaded: {page.url}")
                
                # Handle cookie consent on first page load
                await handle_cookie_consent(page, cookies_loaded=cookies_loaded)
                
                title = await page.title()
                logger.info(f"📄 Page title: {title}")
                
                match = re.search(r"^(.*?)\s(.*?)\s\((.*?)\)", title)
                if not match:
                    logger.error(f"✗ Could not parse brand, model, and generation from title: '{title}'")
                    logger.error(f"   Expected format: 'Brand Model (Generation)'")
                    return
                
                brand_name, model_name, gen_name = match.groups()
                logger.info(f"✓ Parsed page title:")
                logger.info(f"   Brand: {brand_name}")
                logger.info(f"   Model: {model_name}")
                logger.info(f"   Generation: {gen_name}")

                brand, brand_created = get_or_create(db, Brand, name=brand_name.upper())
                model, model_created = get_or_create(db, Model, brand_id=brand.id, name=model_name.upper())
                
                if brand_created:
                    logger.info(f"   ✓ Created brand in DB: {brand_name.upper()}")
                if model_created:
                    logger.info(f"   ✓ Created model in DB: {model_name.upper()}")

                gen, gen_created = get_or_create(
                    db, Generation,
                    model_id=model.id,
                    gen_name=gen_name,
                    defaults={"url": generation_url}
                )
                if gen_created:
                    logger.info(f"   ✓ Created generation in DB: {gen_name}")
                else:
                    logger.info(f"   → Generation already exists: {gen_name}")
                
                await fetch_generation_details(page, db, gen, cookies_loaded=cookies_loaded)

            logger.info("\n💾 Committing database changes...")
            db.commit()
            logger.info("✓ Database changes committed")
            
            # Save cookies/session state for future runs
            logger.info(f"🍪 Saving cookies to {STORAGE_STATE_PATH}...")
            await context.storage_state(path=str(STORAGE_STATE_PATH))
            logger.info(f"✓ Cookies saved")

            logger.info("\n" + "="*100)
            logger.info("✅ SCRAPING COMPLETED SUCCESSFULLY")
            logger.info("="*100)
            logger.info(f"📊 Activity Summary:")
            logger.info(f"   • Main frame navigations: {activity_log['main_frame_navs']}")
            logger.info(f"   • Document requests: {activity_log['document_requests']}")
            logger.info(f"   • Page load events: {activity_log['page_loads']}")
            logger.info(f"   • Total requests: {activity_log['all_requests']}")
            logger.info("="*100 + "\n")

        except Exception as e:
            logger.error("\n" + "="*100)
            logger.error(f"❌ SCRAPING FAILED: {e}")
            logger.error("="*100)
            logger.error("Full error details:", exc_info=True)
            logger.info("🔄 Rolling back database changes...")
            db.rollback()
            logger.info("✓ Database rollback completed")
        finally:
            logger.info("\n🧹 Starting cleanup...")
            logger.info(f"   Active pages in context: {len(context.pages)}")
            for idx, p in enumerate(context.pages, 1):
                logger.info(f"   - Page {idx}: {p.url}")
            
            logger.info("   Closing browser...")
            await browser.close()
            logger.info("✓ Browser closed")
            
            db.close()
            logger.info("✓ Database connection closed\n")


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

