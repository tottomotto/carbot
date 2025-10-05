"""Mobile.bg scraper implementation."""
import re
import time
import random
from typing import List, Dict, Any, Optional
from urllib.parse import urljoin, urlparse
import requests
from bs4 import BeautifulSoup
from config.settings import settings
from scraper.intelligent_extractor import IntelligentFieldExtractor


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
        self.intelligent_extractor = IntelligentFieldExtractor()
    
    def _get_delay(self) -> float:
        """Get random delay between requests."""
        return random.uniform(
            settings.scraper_delay_min,
            settings.scraper_delay_max
        )
    
    def scrape_listings_page(self, url: str) -> List[Dict[str, Any]]:
        """Scrape car listings from a mobile.bg page using intelligent extraction."""
        print(f"Scraping: {url}")
        
        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            listings = []
            
            # Use intelligent extractor to analyze page structure
            print("Analyzing page structure with intelligent extractor...")
            potential_containers = self.intelligent_extractor.analyze_page_structure(soup)
            
            print(f"Found {len(potential_containers)} potential car listing containers")
            
            for i, container_info in enumerate(potential_containers[:15]):  # Limit to top 15
                try:
                    element = container_info['element']
                    fields = container_info['fields']
                    score = container_info['score']
                    
                    print(f"  Container {i+1} (score: {score:.2f}): {len(fields)} fields found")
                    
                    # Extract complete listing using intelligent extractor
                    listing_data = self.intelligent_extractor.extract_car_listing(element)
                    
                    # Set source information
                    listing_data['source_site'] = 'mobile.bg'
                    listing_data['source_url'] = url
                    
                    # Generate consistent source_id
                    import hashlib
                    text_content = element.get_text(strip=True)
                    content_hash = hashlib.md5(text_content[:200].encode()).hexdigest()[:8]
                    listing_data['source_id'] = f"mobile_bg_intelligent_{content_hash}"
                    
                    if listing_data and (listing_data.get('price') or listing_data.get('year') or 'BMW' in text_content):
                        listings.append(listing_data)
                        print(f"    ✓ Extracted: {listing_data.get('title', 'Unknown')[:50]}...")
                        print(f"    Fields: {list(fields.keys())}")
                    else:
                        print(f"    ✗ Skipped: insufficient data")
                        
                except Exception as e:
                    print(f"  ✗ Error extracting container {i+1}: {e}")
                    continue
            
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
                'dealer_name': None,
                'dealer_type': 'unknown',
                'fuel_type': None,
                'transmission': None,
                'body_type': None,
                'color': None,
                'engine_power': None,
                'engine_displacement': None,
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
                        listing['title'] = line
                        break
            
            # Create a proper title if none found or if too long
            if not listing['title'] or len(listing['title']) > 200:
                # Create a clean, short title
                if listing['year'] and listing['price']:
                    listing['title'] = f"BMW M5 {listing['year']} - {listing['price']} {listing['currency']}"
                elif listing['year']:
                    listing['title'] = f"BMW M5 {listing['year']}"
                else:
                    listing['title'] = "BMW M5"
            
            # Final safety check - ensure title is not too long
            if len(listing['title']) > 200:
                listing['title'] = listing['title'][:200]
            
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
            
            # Extract additional car specifications
            # Fuel type
            fuel_patterns = [r'Бензинов', r'Дизел', r'Хибрид', r'Електрически']
            for pattern in fuel_patterns:
                if re.search(pattern, text_content, re.I):
                    listing['fuel_type'] = re.search(pattern, text_content, re.I).group(0)
                    break
            
            # Transmission
            if re.search(r'Автоматична', text_content, re.I):
                listing['transmission'] = 'Автоматична'
            elif re.search(r'Ръчна', text_content, re.I):
                listing['transmission'] = 'Ръчна'
            
            # Body type
            if re.search(r'Седан', text_content, re.I):
                listing['body_type'] = 'Седан'
            elif re.search(r'Купе', text_content, re.I):
                listing['body_type'] = 'Купе'
            elif re.search(r'Кабрио', text_content, re.I):
                listing['body_type'] = 'Кабрио'
            
            # Color
            color_patterns = [r'Черен', r'Бял', r'Син', r'Червен', r'Сребърен', r'Сив']
            for pattern in color_patterns:
                if re.search(pattern, text_content, re.I):
                    listing['color'] = re.search(pattern, text_content, re.I).group(0)
                    break
            
            # Engine power (к.с.)
            power_match = re.search(r'(\d+)\s*к\.с\.', text_content)
            if power_match:
                try:
                    listing['engine_power'] = int(power_match.group(1))
                except ValueError:
                    pass
            
            # Engine displacement (куб.см)
            displacement_match = re.search(r'(\d+)\s*куб\.см', text_content)
            if displacement_match:
                try:
                    displacement_cc = int(displacement_match.group(1))
                    listing['engine_displacement'] = displacement_cc / 1000.0  # Convert to liters
                except ValueError:
                    pass
            
            # Dealer information
            dealer_patterns = [
                r'Дилър:\s*([^,\n]+)',
                r'Автокъща:\s*([^,\n]+)',
                r'Търговец:\s*([^,\n]+)',
            ]
            for pattern in dealer_patterns:
                dealer_match = re.search(pattern, text_content, re.I)
                if dealer_match:
                    listing['dealer_name'] = dealer_match.group(1).strip()
                    listing['dealer_type'] = 'dealer'
                    break
            
            # Check for private seller indicators
            if re.search(r'частно лице|частен|собствен', text_content, re.I):
                listing['dealer_type'] = 'private'
            
            # Extract images
            img_tags = container.find_all('img')
            for img in img_tags:
                src = img.get('src') or img.get('data-src')
                if src:
                    if src.startswith('//'):
                        src = 'https:' + src
                    elif src.startswith('/'):
                        src = urljoin(self.base_url, src)
                    if src.startswith('http') and 'mobile.bg' in src:
                        listing['image_urls'].append(src)
            
            # Generate consistent source_id from URL or specific content
            # Try to find a unique identifier in the content first
            source_id = None
            
            # Look for mobile.bg ad ID patterns (8+ digits)
            ad_id_match = re.search(r'(\d{8,})', text_content)
            if ad_id_match:
                source_id = f"mobile_bg_{ad_id_match.group(1)}"
            else:
                # Look for other unique patterns in the content
                # Try to find a consistent identifier from the content
                import hashlib
                
                # Create a stable hash from key content
                key_parts = []
                if listing.get('title'):
                    key_parts.append(listing['title'][:50])
                if listing.get('price'):
                    key_parts.append(str(listing['price']))
                if listing.get('year'):
                    key_parts.append(str(listing['year']))
                if listing.get('mileage'):
                    key_parts.append(str(listing['mileage']))
                
                if key_parts:
                    key_content = '|'.join(key_parts)
                    # Use MD5 for consistent hashing across sessions
                    content_hash = hashlib.md5(key_content.encode()).hexdigest()[:8]
                    source_id = f"mobile_bg_{content_hash}"
                else:
                    # Last resort: hash of first 100 chars
                    content_hash = hashlib.md5(text_content[:100].encode()).hexdigest()[:8]
                    source_id = f"mobile_bg_{content_hash}"
            
            listing['source_id'] = source_id
            
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
                
                # Generate consistent source_id for alternative extraction
                import hashlib
                context_hash = hashlib.md5(context[:100].encode()).hexdigest()[:8]
                alt_source_id = f"mobile_bg_alt_{i}_{context_hash}"
                
                # Create basic listing
                listing = {
                    'source_site': 'mobile.bg',
                    'source_id': alt_source_id,
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
