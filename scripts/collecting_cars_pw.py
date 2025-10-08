from playwright.sync_api import sync_playwright
from playwright_stealth.stealth import Stealth
import argparse
from pathlib import Path
from urllib.parse import urlparse
import random
import sys
import json
import hashlib
import shutil
from db import SessionLocal, Ad, Image
from datetime import datetime, timezone


def ensure_unique_path(path: Path) -> Path:
    """Return a unique file path by adding a numeric suffix if needed."""
    if not path.exists():
        return path
    stem = path.stem
    suffix = path.suffix
    parent = path.parent
    counter = 1
    while True:
        candidate = parent / f"{stem}-{counter}{suffix}"
        if not candidate.exists():
            return candidate
        counter += 1


def _filename_from_url(url: str) -> str:
    name = Path(urlparse(url).path).name
    return name or "image"


def _accept_cookies(page):
    try:
        page.wait_for_selector('a:has-text("Accept all")', timeout=8000)
        page.click('a:has-text("Accept all")')
        page.wait_for_load_state("domcontentloaded")
    except Exception:
        pass


def _open_first_gallery_item(page):
    # Try clicking a gallery image link to open the lightbox
    for selector in [
        'section a[href*="images.collectingcars.com"]',
        'a[href*="images.collectingcars.com"]',
        'img[loading][src*="images.collectingcars.com"]',
    ]:
        links = page.query_selector_all(selector)
        if links:
            links[0].click()
            return True
    return False


def _find_main_image_locator(page):
    # Prefer lightGallery active slide selectors first
    candidates = [
        '.lg-item.lg-current img.lg-object',
        '.lg-item.lg-current img',
        '.lg-current img',
        'div.lg-outer img.lg-object',
        'div.lg-outer img',
        'img[src*="images.collectingcars.com"]',
        'figure img[src*="images.collectingcars.com"]',
        'div[role="dialog"] img[src*="images.collectingcars.com"]',
        'div[aria-modal="true"] img[src*="images.collectingcars.com"]',
        # Fallback: any visible large img
        'img',
    ]
    for sel in candidates:
        loc = page.locator(sel).filter(has_text=None)
        try:
            loc.first.wait_for(state="visible", timeout=5000)
            return loc.first
        except Exception:
            continue
    return None


def _click_next(page):
    # Try provided XPath first, then multiple next-button selectors; return False if none clickable
    try:
        xpath = "//html/body/div[22]/div/div[3]/button[2]"
        btn = page.locator(f"xpath={xpath}")
        if btn.count() > 0:
            btn.first.click()
            return True
    except Exception:
        pass

    # Fallbacks
    for sel in [
        'button[aria-label="Next slide"]',
        'button.lg-next.lg-icon',
        '.lg-next.lg-icon',
        'button.lg-next',
        '[aria-label="Next slide"]',
        'button[aria-label="Next"]',
        'button:has-text("Next")',
        '[data-slide="next"]',
        'button[title="Next"]',
        'div[role="dialog"] button >> nth=1',  # generic fallback in a modal
    ]:
        try:
            btn = page.locator(sel).first
            if btn.count() > 0:
                btn.click()
                return True
        except Exception:
            continue
    return False


def _pick_best_image_url(img_loc):
    """Pick the highest-quality image URL from the element's src/srcset/data-* attributes."""
    # Prefer srcset largest width if present
    srcset = img_loc.get_attribute("srcset")
    if srcset:
        # srcset format: "url1 320w, url2 640w, ..." or with pixel densities
        candidates = []
        for part in [p.strip() for p in srcset.split(",") if p.strip()]:
            bits = part.split()
            url = bits[0]
            weight = 0
            if len(bits) > 1:
                descriptor = bits[1]
                if descriptor.endswith("w"):
                    try:
                        weight = int(descriptor[:-1])
                    except Exception:
                        weight = 0
                elif descriptor.endswith("x"):
                    try:
                        # multiply by 1000 so 2x > 1000w thumbnails
                        weight = int(float(descriptor[:-1]) * 1000)
                    except Exception:
                        weight = 0
            candidates.append((weight, url))
        if candidates:
            candidates.sort()
            return candidates[-1][1]

    # Fallbacks
    for attr in ["src", "data-src", "data-original", "data-lg-src"]:
        val = img_loc.get_attribute(attr)
        if val:
            return val
    return None


def _get_element_current_src(page, img_loc):
    """Use the browser's chosen resource via HTMLImageElement.currentSrc, fallback to src.
    Always resolve to absolute URL using the page URL as base.
    """
    try:
        current = page.evaluate(
            "(el) => el.currentSrc || el.src || null",
            img_loc.element_handle(),
        )
    except Exception:
        current = None
    if not current:
        current = _pick_best_image_url(img_loc)
    if not current:
        return None
    try:
        # Resolve relative URLs against the current page URL
        abs_url = page.evaluate(
            "(args) => new URL(args.u, args.base).toString()",
            {"u": current, "base": page.url},
        )
        return abs_url
    except Exception:
        return current


def _wait_for_image_loaded(page, img_loc, timeout_ms=8000):
    """Wait until the image has a positive naturalWidth/Height (loaded)."""
    try:
        page.wait_for_function(
            "(el) => el && el.naturalWidth > 0 && el.naturalHeight > 0",
            arg=img_loc.element_handle(),
            timeout=timeout_ms,
        )
        return True
    except Exception:
        return False


def _wait_for_new_image(page, previous_url: str | None, timeout_ms=12000) -> bool:
    """Wait until the currently visible gallery image has a different currentSrc/src from previous_url and is loaded."""
    try:
        page.wait_for_function(
            "(prev) => {\n"
            "  const imgs = Array.from(document.querySelectorAll('img'));\n"
            "  // Prefer images hosted by images.collectingcars.com if present\n"
            "  const candidates = imgs.filter(el => (el.currentSrc || el.src || '').includes('images.collectingcars.com'));\n"
            "  const pool = candidates.length ? candidates : imgs;\n"
            "  // Choose the largest visible image\n"
            "  let best = null; let bestArea = 0;\n"
            "  for (const el of pool) {\n"
            "    const rect = el.getBoundingClientRect();\n"
            "    const area = Math.max(0, rect.width) * Math.max(0, rect.height);\n"
            "    const visible = !!(el.offsetParent || (rect.width && rect.height));\n"
            "    if (visible && area > bestArea) { bestArea = area; best = el; }\n"
            "  }\n"
            "  if (!best) return false;\n"
            "  const src = best.currentSrc || best.src || null;\n"
            "  if (!src) return false;\n"
            "  if (prev && src === prev) return false;\n"
            "  return best.naturalWidth > 0 && best.naturalHeight > 0;\n"
            "}",
            arg=previous_url,
            timeout=timeout_ms,
        )
        return True
    except Exception:
        return False


def _get_download_href(page):
    """Try to read the lightGallery download link href (e.g., a#lg-download)."""
    for sel in [
        'a#lg-download',
        'a.lg-download',
        '.lg-download',
        'div.lg-outer a[download]'
    ]:
        try:
            loc = page.locator(sel).first
            if loc.count() > 0:
                href = loc.get_attribute('href')
                if href:
                    return href
        except Exception:
            continue
    return None


def _download_via_new_tab(page, url: str, outpath: Path, referer: str) -> bool:
    """Open image URL in a new tab with Referer, save response body if OK."""
    try:
        ctx = page.context
        img_page = ctx.new_page()
        resp = img_page.goto(url, wait_until='load', referer=referer)
        if resp and resp.ok:
            # Optional: ensure it's an image
            ctype = resp.headers.get('content-type', '') if hasattr(resp, 'headers') else ''
            if 'image' in ctype or url.lower().endswith(('.jpg', '.jpeg', '.png', '.webp')):
                with open(outpath, 'wb') as f:
                    f.write(resp.body())
                img_page.close()
                return True
        img_page.close()
    except Exception:
        pass
    return False

def calculate_checksum(file_path):
    """Calculates the SHA256 checksum of a file."""
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256.update(byte_block)
    return sha256.hexdigest()

def store_image(temp_path: Path, storage_root: Path) -> tuple[Path, str]:
    """Calculates checksum and moves image to content-addressable storage."""
    checksum = calculate_checksum(temp_path)
    dest_dir = storage_root / checksum[:2] / checksum[2:4]
    dest_dir.mkdir(parents=True, exist_ok=True)
    final_path = dest_dir / temp_path.name
    shutil.move(temp_path, final_path)
    return final_path, checksum

def _scrape_structured_data(page) -> dict:
    """Scrapes key structured data from the ad page."""
    data = {}
    try:
        # Car Overview Section
        overview_selector = 'h2:has-text("Car Overview") + ul'
        overview_list = page.locator(overview_selector)
        if overview_list.count() > 0:
            items = overview_list.locator("li").all()
            for item in items:
                text = item.inner_text()
                if not text:
                    continue
                # Simple pattern matching for now
                if "miles" in text.lower() or "km" in text.lower():
                    data["mileage"] = text
                elif "rhd" in text.lower() or "lhd" in text.lower():
                    data["drive"] = text
                elif "automatic" in text.lower() or "manual" in text.lower():
                    data["transmission"] = text
                else:
                    # Attempt to identify color vs. interior vs. engine
                    # This is naive and can be improved with better selectors
                    if "color" not in data:
                        data["color"] = text
                    elif "engine" not in data:
                        data["engine"] = text

        # Lot Overview Section for location
        lot_selector = 'h2:has-text("Lot Overview") + ul'
        lot_list = page.locator(lot_selector)
        if lot_list.count() > 0:
            # Location is typically the last item
            location_item = lot_list.locator("li").last
            if location_item and "United Kingdom" in location_item.inner_text(): # a bit specific
                 data["location"] = location_item.inner_text()
            elif lot_list.locator("li >> nth=-1"):
                 data["location"] = lot_list.locator("li >> nth=-1").inner_text()


    except Exception as e:
        print(f"Could not parse all structured data: {e}")
    
    return data

def main():
    parser = argparse.ArgumentParser(description="CollectingCars ad scraper")
    parser.add_argument("url", help="Full URL of the CollectingCars listing to scrape.")
    parser.add_argument(
        "--storage-dir",
        default="datasets/storage",
        help="Base directory for content-addressable image storage (default: 'datasets/storage')",
    )
    parser.add_argument("--headless", action="store_true", default=True)
    parser.add_argument("--limit", type=int, default=20, help="Max number of new images to save.")
    parser.add_argument("--delay-ms", type=int, default=1000, help="Delay between slides (ms).")
    args = parser.parse_args()

    storage_root = Path(args.storage_dir)
    storage_root.mkdir(parents=True, exist_ok=True)
    temp_dir = storage_root / "temp"
    temp_dir.mkdir(exist_ok=True)

    db = SessionLocal()
    try:
        with Stealth().use_sync(sync_playwright()) as p:
            browser = p.chromium.launch(headless=args.headless)
            page = browser.new_context().new_page()
            page.goto(args.url, wait_until="domcontentloaded")

            _accept_cookies(page)
            page.wait_for_timeout(1000)

            # --- Scrape all textual data first ---
            title = page.title()
            print(f"Scraping ad: {title}")
            structured_data = _scrape_structured_data(page)
            print(f"Scraped structured data: {structured_data}")

            # --- Check for existing ad and decide whether to create or update ---
            source_site = urlparse(args.url).netloc
            source_id = Path(urlparse(args.url).path).name
            ad_record = db.query(Ad).filter_by(source_site=source_site, source_id=source_id).first()
            is_new_ad = False

            if ad_record:
                print(f"Found existing Ad record (ID: {ad_record.id}). Checking for updates...")
                ad_record.raw_title = title
                ad_record.raw_data = structured_data
                ad_record.last_scraped_at = datetime.now(timezone.utc)
            else:
                is_new_ad = True
                print("Creating new Ad record...")
                ad_record = Ad(
                    source_site=source_site,
                    source_id=source_id,
                    source_url=args.url,
                    raw_title=title,
                    raw_data=structured_data,
                    is_active=True
                )
                db.add(ad_record)
                db.flush()

            if not _open_first_gallery_item(page):
                print("Could not open gallery lightbox, will scan for images on page.")

            new_images_to_commit = []
            seen_urls = set()
            
            # Initialize last_url to the currently displayed image when gallery opens
            cur_loc = _find_main_image_locator(page)
            last_url = _get_element_current_src(page, cur_loc) if cur_loc else None
            if last_url:
                seen_urls.add(last_url)

            while len(new_images_to_commit) < args.limit:
                img_loc = _find_main_image_locator(page)
                if not img_loc:
                    print("Could not find main image locator. Ending.")
                    break

                try:
                    page.wait_for_timeout(args.delay_ms)
                    _wait_for_image_loaded(page, img_loc, timeout_ms=10000)
                    
                    target_url = _get_element_current_src(page, img_loc)
                    if not target_url or target_url in seen_urls:
                        # If we've seen this URL or can't find one, try advancing.
                        if not _click_next(page): break
                        continue

                    seen_urls.add(target_url)
                    fname = _filename_from_url(target_url)
                    if not fname.lower().endswith((".jpg", ".jpeg", ".png", ".webp")):
                        fname += ".jpg"
                    
                    temp_path = ensure_unique_path(temp_dir / fname)
                    
                    if _download_via_new_tab(page, target_url, temp_path, referer=args.url):
                        final_path, checksum = store_image(temp_path, storage_root)
                        
                        image_exists = db.query(Image.id).filter_by(checksum=checksum).first()
                        if not image_exists:
                            new_image = Image(
                                ad_id=ad_record.id,
                                image_uri=final_path.as_posix(),
                                checksum=checksum,
                                status='raw'
                            )
                            new_images_to_commit.append(new_image)
                            print(f"Queued new image: {final_path.name} (checksum: {checksum[:10]}...)")
                        else:
                            print(f"Image exists (checksum: {checksum[:10]}...). Skipping.")
                            # Clean up the redundant download
                            final_path.unlink()

                    else:
                        print(f"Failed to download image from {target_url}")

                except Exception as e:
                    print(f"Error processing image: {e}")

                if not _click_next(page):
                    print("Could not find next button. Ending.")
                    break
                
                if not _wait_for_new_image(page, last_url, timeout_ms=max(8000, args.delay_ms + 3000)):
                    page.wait_for_timeout(int(args.delay_ms * 1.5))
                
                next_img_loc = _find_main_image_locator(page)
                if next_img_loc:
                    last_url = _get_element_current_src(page, next_img_loc)

            # --- Final Commit Logic ---
            changes_made = db.is_modified(ad_record) or new_images_to_commit

            if new_images_to_commit:
                db.add_all(new_images_to_commit)

            if is_new_ad and not new_images_to_commit:
                db.rollback()
                print("\nNo new images found for this new ad. No database changes were made.")
            elif changes_made:
                db.commit()
                action = "Created" if is_new_ad else "Updated"
                print(f"\nSUCCESS: {action} Ad record (ID: {ad_record.id}) and added {len(new_images_to_commit)} new images.")
            else:
                print("\nNo changes detected. Database is already up to date.")

            browser.close()
    finally:
        db.close()

if __name__ == "__main__":
    project_root = Path(__file__).resolve().parents[1]
    sys.path.append(str(project_root))
    main()