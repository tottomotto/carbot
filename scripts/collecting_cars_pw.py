from playwright.sync_api import sync_playwright
from playwright_stealth.stealth import Stealth
import argparse
from pathlib import Path
from urllib.parse import urlparse
import random

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

def main():
    parser = argparse.ArgumentParser(description="CollectingCars image downloader (UI-driven)")
    parser.add_argument("make", help="Vehicle make directory (e.g. 'bmw')")
    parser.add_argument("variant", help="Model/variant directory (e.g. 'f90-lci-cs')")
    parser.add_argument(
        "--base-dir",
        default="datasets",
        help="Base directory to store images (default: 'datasets')",
    )
    parser.add_argument(
        "--url",
        default="https://collectingcars.com/for-sale/2022-bmw-f90-m5-cs-4",
        help="CollectingCars listing URL to scrape",
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        default=True,
        help="Run browser in headless mode",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=25,
        help="Max number of gallery images to save via screenshots",
    )
    parser.add_argument(
        "--delay-ms",
        type=int,
        default=1000,
        help="Delay between slides (ms) to allow image to render",
    )
    args = parser.parse_args()

    output_dir = (Path(args.base_dir) if Path(args.base_dir).is_absolute() else Path.cwd() / args.base_dir) / args.make / args.variant
    output_dir.mkdir(parents=True, exist_ok=True)

    # Wrap Playwright with stealth so new contexts/pages are auto-patched.
    with Stealth().use_sync(sync_playwright()) as p:
        browser = p.chromium.launch(headless=args.headless)
        context = browser.new_context()
        page = context.new_page()
        page.goto(args.url, wait_until="domcontentloaded")

        _accept_cookies(page)
        page.wait_for_timeout(1000)

        if not _open_first_gallery_item(page):
            # If lightbox didn't open, fall back to scanning page without modal
            pass

        saved = 0
        # Initialize last_url to the currently displayed image when gallery opens
        cur_loc = _find_main_image_locator(page)
        last_url = _get_element_current_src(page, cur_loc) if cur_loc else None

        while saved < args.limit:
            img_loc = _find_main_image_locator(page)
            if not img_loc:
                break

            # Ensure the image is fully loaded
            try:
                page.wait_for_timeout(args.delay_ms)
                _wait_for_image_loaded(page, img_loc, timeout_ms=10000)
                # Resolve the actual image URL that the browser is displaying
                best_url = _get_element_current_src(page, img_loc)
                if best_url:
                    fname = _filename_from_url(best_url)
                else:
                    fname = f"image-{saved+1}.jpg"
                if not fname.lower().endswith((".jpg", ".jpeg", ".png", ".webp")):
                    fname += ".jpg"
                outpath = ensure_unique_path(output_dir / fname)

                did_save = False
                # 1) Prefer the lightbox's download link if present
                dl_href = _get_download_href(page)
                resolved_dl = page.evaluate("(args) => args.u ? new URL(args.u, args.base).toString() : null", {"u": dl_href, "base": page.url}) if dl_href else None
                # 2) Otherwise use the currentSrc URL
                target_url = resolved_dl or best_url

                if target_url:
                    # Try opening in a new tab (helps with Cloudflare/anti-bot)
                    if _download_via_new_tab(page, target_url, outpath, referer=args.url):
                        print(f"Saved: {outpath}")
                        saved += 1
                        did_save = True
                    else:
                        # Fall back to API request in the same browser context
                        try:
                            resp = page.request.get(
                                target_url,
                                headers={
                                    "Referer": args.url,
                                    "User-Agent": page.evaluate("() => navigator.userAgent"),
                                    "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
                                    "Accept-Language": "en-US,en;q=0.9",
                                },
                            )
                            if resp.ok:
                                with open(outpath, "wb") as f:
                                    f.write(resp.body())
                                print(f"Saved: {outpath}")
                                saved += 1
                                did_save = True
                            else:
                                print(f"HTTP {resp.status} for {target_url}, falling back to screenshot")
                        except Exception as e:
                            print(f"Failed HTTP download for {target_url}: {e}")

                if not did_save:
                    # Screenshot the element as a fallback
                    img_loc.screenshot(path=str(outpath), type="jpeg", quality=95)
                    print(f"Saved (screenshot): {outpath}")
                    saved += 1
            except Exception as e:
                print(f"Failed to capture image {saved+1}: {e}")

            # Advance to next slide; if not possible, stop
            if not _click_next(page):
                break

            # Wait for the next image to be different and fully loaded
            if not _wait_for_new_image(page, last_url, timeout_ms=max(8000, args.delay_ms + 3000)):
                # If not detected, still pause a bit as fallback
                jitter = int(args.delay_ms * (0.8 + random.random()))
                page.wait_for_timeout(jitter)

            # Update last_url to the newly visible image
            next_img_loc = _find_main_image_locator(page)
            if next_img_loc:
                last_url = _get_element_current_src(page, next_img_loc)

        print(f"Downloaded {saved} images to {output_dir}")

        if not args.headless:
            input("Press Enter to exit...")
        browser.close()

if __name__ == "__main__":
    main()