"""Mobile.bg scraper implementation."""
import re
import time
import random
from typing import List, Dict, Any, Optional
from urllib.parse import urljoin, urlparse
import requests
from bs4 import BeautifulSoup
from config.settings import settings


class MobileBgScraper:
    """Scraper for mobile.bg car listings."""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': settings.scraper_user_agent,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })
        self.base_url = "https://www.mobile.bg"
    
    def _get_delay(self) -> float:
        """Get random delay between requests."""
        return random.uniform(
            settings.scraper_delay_min,
            settings.scraper_delay_max
        )
    
    def scrape_listings_page(self, url: str) -> List[Dict[str, Any]]:
        """Scrape car listings from a mobile.bg page."""
        print(f"Scraping: {url}")
        
        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            listings = []
            
            # Find car listing containers
            # Based on the HTML structure, listings appear to be in specific containers
            listing_containers = soup.find_all('div', class_=re.compile(r'.*listing.*|.*car.*|.*ad.*'))
            
            # If no specific containers found, look for common patterns
            if not listing_containers:
                # Look for elements that might contain car info
                listing_containers = soup.find_all('div', string=re.compile(r'BMW.*M5', re.I))
            
            # Alternative approach: look for price patterns
            if not listing_containers:
                price_elements = soup.find_all(text=re.compile(r'\d+\s*\d*\s*[лв|€|$]'))
                for price_elem in price_elements:
                    parent = price_elem.parent
                    if parent and parent not in listing_containers:
                        listing_containers.append(parent)
            
            print(f"Found {len(listing_containers)} potential listing containers")
            
            for i, container in enumerate(listing_containers[:20]):  # Limit to first 20
                try:
                    listing_data = self._extract_listing_data(container, url)
                    if listing_data:
                        listings.append(listing_data)
                        print(f"  ✓ Extracted listing {i+1}: {listing_data.get('title', 'Unknown')[:50]}...")
                except Exception as e:
                    print(f"  ✗ Error extracting listing {i+1}: {e}")
                    continue
            
            # If we didn't find much with containers, try a different approach
            if len(listings) < 5:
                print("Trying alternative extraction method...")
                alternative_listings = self._extract_alternative(soup, url)
                listings.extend(alternative_listings)
            
            print(f"Total listings extracted: {len(listings)}")
            return listings
            
        except requests.RequestException as e:
            print(f"Request error: {e}")
            return []
        except Exception as e:
            print(f"Parsing error: {e}")
            return []
    
    def _extract_listing_data(self, container, page_url: str) -> Optional[Dict[str, Any]]:
        """Extract data from a single listing container."""
        try:
            # Initialize listing data
            listing = {
                'source_site': 'mobile.bg',
                'source_url': page_url,
                'raw_data': {},
                'title': None,
                'price': None,
                'currency': 'лв',  # Bulgarian Lev
                'year': None,
                'make': 'BMW',
                'model': 'M5',
                'mileage': None,
                'location': None,
                'image_urls': [],
            }
            
            # Extract text content
            text_content = container.get_text(strip=True)
            listing['raw_data']['text_content'] = text_content
            
            # Look for price patterns (Bulgarian format: 109 999 лв)
            # Try multiple price patterns
            price_patterns = [
                r'(\d+(?:\s+\d+)*)\s*(лв|€|\$)',
                r'(\d+(?:\.\d+)?)\s*(лв|€|\$)',
                r'(\d+(?:,\d+)?)\s*(лв|€|\$)',
            ]
            
            for pattern in price_patterns:
                price_match = re.search(pattern, text_content)
                if price_match:
                    price_str = price_match.group(1).replace(' ', '').replace(',', '')
                    try:
                        price_val = float(price_str)
                        # Filter out unrealistic prices (too low or too high)
                        if 10000 <= price_val <= 500000:
                            listing['price'] = price_val
                            listing['currency'] = price_match.group(2)
                            break
                    except ValueError:
                        continue
            
            # Look for year (2019+)
            year_match = re.search(r'(20\d{2})', text_content)
            if year_match:
                year = int(year_match.group(1))
                if year >= 2019:
                    listing['year'] = year
            
            # Look for mileage (км) - try different patterns
            mileage_patterns = [
                r'(\d+(?:\s+\d+)*)\s*км',
                r'(\d+(?:\.\d+)?)\s*км',
                r'(\d+(?:,\d+)?)\s*км',
            ]
            
            for pattern in mileage_patterns:
                mileage_match = re.search(pattern, text_content)
                if mileage_match:
                    mileage_str = mileage_match.group(1).replace(' ', '').replace(',', '')
                    try:
                        mileage_val = int(mileage_str)
                        # Filter out unrealistic mileage
                        if 0 <= mileage_val <= 500000:
                            listing['mileage'] = mileage_val
                            break
                    except ValueError:
                        continue
            
            # Extract title from text or nearby elements
            if 'BMW' in text_content and 'M5' in text_content:
                # Try to find a meaningful title
                lines = [line.strip() for line in text_content.split('\n') if line.strip()]
                for line in lines:
                    if 'BMW' in line and 'M5' in line and len(line) > 10:
                        listing['title'] = line[:200]  # Limit title length
                        break
            
            # If no title found, create a basic one
            if not listing['title']:
                year_str = f" {listing['year']}" if listing['year'] else ""
                price_str = f" - {listing['price']} {listing['currency']}" if listing['price'] else ""
                listing['title'] = f"BMW M5{year_str}{price_str}"[:200]
            
            # Look for location
            location_patterns = [
                r'гр\.\s*([^,\n]+)',
                r'София|Пловдив|Варна|Бургас|Русе|Стара Загора|Плевен',
            ]
            for pattern in location_patterns:
                location_match = re.search(pattern, text_content, re.I)
                if location_match:
                    listing['location'] = location_match.group(1) if location_match.groups() else location_match.group(0)
                    break
            
            # Extract images
            img_tags = container.find_all('img')
            for img in img_tags:
                src = img.get('src') or img.get('data-src')
                if src:
                    if src.startswith('//'):
                        src = 'https:' + src
                    elif src.startswith('/'):
                        src = urljoin(self.base_url, src)
                    if src.startswith('http'):
                        listing['image_urls'].append(src)
            
            # Generate source_id from content hash
            content_hash = hash(text_content[:100])
            listing['source_id'] = f"mobile_bg_{abs(content_hash)}"
            
            # Only return if we have meaningful data
            if listing['price'] or listing['year'] or 'BMW M5' in text_content:
                return listing
            
        except Exception as e:
            print(f"Error extracting listing data: {e}")
        
        return None
    
    def _extract_alternative(self, soup: BeautifulSoup, page_url: str) -> List[Dict[str, Any]]:
        """Alternative extraction method when containers don't work."""
        listings = []
        
        # Look for all text that mentions BMW M5
        bmw_m5_texts = soup.find_all(text=re.compile(r'BMW.*M5', re.I))
        
        for i, text_elem in enumerate(bmw_m5_texts[:10]):  # Limit to 10
            try:
                # Get the parent element
                parent = text_elem.parent
                if not parent:
                    continue
                
                # Get surrounding context
                context = parent.get_text(strip=True)
                
                # Create basic listing
                listing = {
                    'source_site': 'mobile.bg',
                    'source_id': f"mobile_bg_alt_{i}_{hash(context[:50])}",
                    'source_url': page_url,
                    'raw_data': {'text_content': context},
                    'title': f"BMW M5 - {context[:100]}",
                    'make': 'BMW',
                    'model': 'M5',
                    'currency': 'лв',
                    'image_urls': [],
                }
                
                # Try to extract price
                price_match = re.search(r'(\d+(?:\s+\d+)*)\s*(лв|€|\$)', context)
                if price_match:
                    price_str = price_match.group(1).replace(' ', '')
                    try:
                        listing['price'] = float(price_str)
                        listing['currency'] = price_match.group(2)
                    except ValueError:
                        pass
                
                # Try to extract year
                year_match = re.search(r'(20\d{2})', context)
                if year_match:
                    year = int(year_match.group(1))
                    if year >= 2019:
                        listing['year'] = year
                
                # Try to extract mileage
                mileage_match = re.search(r'(\d+(?:\s+\d+)*)\s*км', context)
                if mileage_match:
                    mileage_str = mileage_match.group(1).replace(' ', '')
                    try:
                        listing['mileage'] = int(mileage_str)
                    except ValueError:
                        pass
                
                listings.append(listing)
                
            except Exception as e:
                print(f"Error in alternative extraction: {e}")
                continue
        
        return listings
    
    def close(self):
        """Close the session."""
        self.session.close()


def scrape_mobile_bg_bmw_m5(url: str) -> List[Dict[str, Any]]:
    """Main function to scrape BMW M5 listings from mobile.bg."""
    scraper = MobileBgScraper()
    try:
        listings = scraper.scrape_listings_page(url)
        return listings
    finally:
        scraper.close()


if __name__ == "__main__":
    # Test the scraper
    test_url = "https://www.mobile.bg/obiavi/avtomobili-dzhipove/bmw/m5/ot-2019"
    listings = scrape_mobile_bg_bmw_m5(test_url)
    
    print(f"\n=== SCRAPING RESULTS ===")
    print(f"Total listings found: {len(listings)}")
    
    for i, listing in enumerate(listings[:5], 1):  # Show first 5
        print(f"\n--- Listing {i} ---")
        print(f"Title: {listing.get('title', 'N/A')}")
        print(f"Price: {listing.get('price', 'N/A')} {listing.get('currency', '')}")
        print(f"Year: {listing.get('year', 'N/A')}")
        print(f"Mileage: {listing.get('mileage', 'N/A')} km")
        print(f"Location: {listing.get('location', 'N/A')}")
        print(f"Source ID: {listing.get('source_id', 'N/A')}")
