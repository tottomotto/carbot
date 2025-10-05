"""Intelligent field extraction system that works across different sites and languages."""
import re
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from bs4 import BeautifulSoup, Tag


@dataclass
class FieldPattern:
    """Pattern for detecting a specific field type."""
    name: str
    patterns: List[str]
    score: float
    data_type: str
    validation_func: Optional[callable] = None


class IntelligentFieldExtractor:
    """Intelligent field extractor that uses pattern matching and scoring."""
    
    def __init__(self):
        self.field_patterns = self._initialize_patterns()
    
    def _initialize_patterns(self) -> List[FieldPattern]:
        """Initialize field detection patterns."""
        return [
            # Price patterns (multiple currencies and formats)
            FieldPattern(
                name="price",
                patterns=[
                    r'(\d+(?:[\s,\.]\d+)*)\s*(лв|€|\$|USD|EUR|BGN|лева|евро|долара)',
                    r'(\d+(?:[\s,\.]\d+)*)\s*(лв|€|\$)',
                    r'(\d+(?:,\d+)?)\s*(лв|€|\$)',
                    r'(\d+(?:\.\d+)?)\s*(лв|€|\$)',
                ],
                score=0.9,
                data_type="float",
                validation_func=lambda x: 1000 <= x <= 1000000
            ),
            
            # Year patterns
            FieldPattern(
                name="year",
                patterns=[
                    r'(20\d{2})',
                    r'(19\d{2})',
                    r'(\d{4})\s*г\.',
                    r'(\d{4})\s*год',
                ],
                score=0.95,
                data_type="int",
                validation_func=lambda x: 1990 <= x <= 2030
            ),
            
            # Mileage patterns (multiple languages)
            FieldPattern(
                name="mileage",
                patterns=[
                    r'(\d+(?:[\s,\.]\d+)*)\s*км',
                    r'(\d+(?:[\s,\.]\d+)*)\s*mile',
                    r'(\d+(?:[\s,\.]\d+)*)\s*km',
                    r'(\d+(?:,\d+)?)\s*км',
                    r'(\d+(?:\.\d+)?)\s*км',
                ],
                score=0.9,
                data_type="int",
                validation_func=lambda x: 0 <= x <= 1000000
            ),
            
            # Engine power patterns
            FieldPattern(
                name="engine_power",
                patterns=[
                    r'(\d+)\s*к\.с\.',
                    r'(\d+)\s*hp',
                    r'(\d+)\s*PS',
                    r'(\d+)\s*horsepower',
                    r'(\d+)\s*к\.с',
                ],
                score=0.85,
                data_type="int",
                validation_func=lambda x: 50 <= x <= 2000
            ),
            
            # Engine displacement patterns
            FieldPattern(
                name="engine_displacement",
                patterns=[
                    r'(\d+)\s*куб\.см',
                    r'(\d+(?:\.\d+)?)\s*L',
                    r'(\d+(?:\.\d+)?)\s*л',
                    r'(\d+(?:\.\d+)?)\s*liter',
                ],
                score=0.8,
                data_type="float",
                validation_func=lambda x: 0.5 <= x <= 10.0
            ),
            
            # Fuel type patterns
            FieldPattern(
                name="fuel_type",
                patterns=[
                    r'(Бензинов|Дизел|Хибрид|Електрически)',
                    r'(Gasoline|Diesel|Hybrid|Electric)',
                    r'(Benzin|Diesel|Hybrid|Elektro)',
                    r'(Essence|Diesel|Hybride|Électrique)',
                ],
                score=0.7,
                data_type="string",
                validation_func=None
            ),
            
            # Transmission patterns
            FieldPattern(
                name="transmission",
                patterns=[
                    r'(Автоматична|Ръчна)',
                    r'(Automatic|Manual)',
                    r'(Automatik|Schaltgetriebe)',
                    r'(Automatique|Manuelle)',
                ],
                score=0.7,
                data_type="string",
                validation_func=None
            ),
            
            # Body type patterns
            FieldPattern(
                name="body_type",
                patterns=[
                    r'(Седан|Купе|Кабрио|Хечбек|СУВ|Пикап)',
                    r'(Sedan|Coupe|Convertible|Hatchback|SUV|Pickup)',
                    r'(Limousine|Coupé|Cabrio|Kombi|SUV)',
                ],
                score=0.6,
                data_type="string",
                validation_func=None
            ),
            
            # Color patterns
            FieldPattern(
                name="color",
                patterns=[
                    r'(Черен|Бял|Син|Червен|Сребърен|Сив|Зелен|Жълт)',
                    r'(Black|White|Blue|Red|Silver|Gray|Green|Yellow)',
                    r'(Schwarz|Weiß|Blau|Rot|Silber|Grau|Grün|Gelb)',
                    r'(Noir|Blanc|Bleu|Rouge|Argent|Gris|Vert|Jaune)',
                ],
                score=0.5,
                data_type="string",
                validation_func=None
            ),
            
            # Location patterns
            FieldPattern(
                name="location",
                patterns=[
                    r'гр\.\s*([^,\n]+)',
                    r'(София|Пловдив|Варна|Бургас|Русе|Стара Загора|Плевен)',
                    r'(Sofia|Plovdiv|Varna|Burgas|Ruse)',
                ],
                score=0.6,
                data_type="string",
                validation_func=None
            ),
        ]
    
    def extract_fields_from_text(self, text: str) -> Dict[str, Any]:
        """Extract fields from text using intelligent pattern matching."""
        results = {}
        
        for pattern in self.field_patterns:
            best_match = None
            best_score = 0
            
            for regex in pattern.patterns:
                matches = re.finditer(regex, text, re.IGNORECASE)
                for match in matches:
                    try:
                        # Extract and convert value
                        value = self._extract_value(match, pattern.data_type)
                        
                        # Validate if validation function exists
                        if pattern.validation_func and not pattern.validation_func(value):
                            continue
                        
                        # Score this match
                        score = pattern.score
                        
                        # Bonus for longer matches (more specific)
                        score += len(match.group(0)) * 0.01
                        
                        if score > best_score:
                            best_match = {
                                'value': value,
                                'raw_match': match.group(0),
                                'score': score
                            }
                            best_score = score
                    
                    except (ValueError, IndexError):
                        continue
            
            if best_match:
                results[pattern.name] = best_match['value']
        
        return results
    
    def _extract_value(self, match, data_type: str) -> Any:
        """Extract and convert value from regex match."""
        if data_type == "float":
            # Try to extract numeric value from first group
            value_str = match.group(1).replace(' ', '').replace(',', '')
            return float(value_str)
        elif data_type == "int":
            # Try to extract numeric value from first group
            value_str = match.group(1).replace(' ', '').replace(',', '')
            return int(value_str)
        else:  # string
            return match.group(0).strip()
    
    def extract_from_html_element(self, element: Tag) -> Dict[str, Any]:
        """Extract fields from an HTML element."""
        # Get all text content
        text_content = element.get_text(strip=True)
        
        # Also check individual child elements for more precise extraction
        child_results = {}
        for child in element.find_all(['span', 'div', 'p']):
            child_text = child.get_text(strip=True)
            if child_text:
                child_fields = self.extract_fields_from_text(child_text)
                for field, value in child_fields.items():
                    if field not in child_results:
                        child_results[field] = value
        
        # Extract images from this element
        image_urls = self._extract_images_from_element(element)
        if image_urls:
            child_results['image_urls'] = image_urls
        
        # Combine results, preferring child element results for precision
        main_results = self.extract_fields_from_text(text_content)
        
        # Merge results, child results take precedence
        final_results = {**main_results, **child_results}
        
        return final_results
    
    def _extract_images_from_element(self, element: Tag) -> List[str]:
        """Extract image URLs from an HTML element."""
        image_urls = []
        
        # Look for img tags
        img_tags = element.find_all('img')
        for img in img_tags:
            src = img.get('src') or img.get('data-src')
            if src:
                # Convert relative URLs to absolute
                if src.startswith('//'):
                    src = 'https:' + src
                elif src.startswith('/'):
                    src = 'https://www.mobile.bg' + src
                elif not src.startswith('http'):
                    src = 'https://www.mobile.bg/' + src
                
                # Filter out non-car images
                if self._is_car_image(src):
                    image_urls.append(src)
        
        # Look for background images in style attributes
        elements_with_bg = element.find_all(attrs={'style': True})
        for elem in elements_with_bg:
            style = elem.get('style', '')
            bg_match = re.search(r'background-image:\s*url\(["\']?([^"\']+)["\']?\)', style)
            if bg_match:
                src = bg_match.group(1)
                if src.startswith('//'):
                    src = 'https:' + src
                elif src.startswith('/'):
                    src = 'https://www.mobile.bg' + src
                elif not src.startswith('http'):
                    src = 'https://www.mobile.bg/' + src
                
                if self._is_car_image(src):
                    image_urls.append(src)
        
        return list(set(image_urls))  # Remove duplicates
    
    def _is_car_image(self, url: str) -> bool:
        """Check if an image URL is likely a car image."""
        # Skip common non-car images
        skip_patterns = [
            'logo', 'icon', 'nophoto', 'placeholder', 'banner', 'advertisement',
            'social', 'facebook', 'twitter', 'instagram', 'youtube', 'google',
            'analytics', 'tracking', 'pixel', 'beacon'
        ]
        
        url_lower = url.lower()
        for pattern in skip_patterns:
            if pattern in url_lower:
                return False
        
        # Look for car-related patterns
        car_patterns = [
            'photo', 'image', 'car', 'auto', 'vehicle', 'mobile.bg',
            'focus.bg', 'picturess', 'photosorg'
        ]
        
        for pattern in car_patterns:
            if pattern in url_lower:
                return True
        
        # If it's from mobile.bg or focus.bg domains, likely a car image
        if 'mobile.bg' in url_lower or 'focus.bg' in url_lower:
            return True
        
        return False
    
    def analyze_page_structure(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """Analyze page structure to find potential car listing containers."""
        containers = []
        
        # Strategy 1: Look for elements with high field density
        all_elements = soup.find_all(['div', 'article', 'section', 'li'])
        
        for i, element in enumerate(all_elements):
            if not element.get_text(strip=True):
                continue
                
            # Extract fields from this element
            fields = self.extract_from_html_element(element)
            
            if len(fields) >= 2:  # At least 2 fields found
                score = sum(len(str(v)) for v in fields.values()) / len(fields)
                containers.append({
                    'element': element,
                    'fields': fields,
                    'score': score,
                    'page_order': i,  # Preserve original page order
                    'text_preview': element.get_text(strip=True)[:200]
                })
        
        # Sort by score (highest first), but preserve page order for same scores
        containers.sort(key=lambda x: (x['score'], -x['page_order']), reverse=True)
        
        return containers[:20]  # Return top 20 candidates
    
    def extract_car_listing(self, element: Tag) -> Dict[str, Any]:
        """Extract a complete car listing from an HTML element."""
        # Extract all fields
        fields = self.extract_from_html_element(element)
        
        # Create structured listing
        listing = {
            'source_site': 'unknown',
            'source_id': 'unknown',
            'source_url': 'unknown',
            'raw_data': {'text_content': element.get_text(strip=True)},
            'title': None,
            'price': fields.get('price'),
            'currency': self._extract_currency(element.get_text()),
            'year': fields.get('year'),
            'make': 'BMW',  # Default for this scraper
            'model': 'M5',  # Default for this scraper
            'mileage': fields.get('mileage'),
            'location': fields.get('location'),
            'dealer_name': None,
            'dealer_type': 'unknown',
            'fuel_type': fields.get('fuel_type'),
            'transmission': fields.get('transmission'),
            'body_type': fields.get('body_type'),
            'color': fields.get('color'),
            'engine_power': fields.get('engine_power'),
            'engine_displacement': fields.get('engine_displacement'),
            'image_urls': fields.get('image_urls', []),
        }
        
        # Generate title
        title_parts = []
        if listing['year']:
            title_parts.append(str(listing['year']))
        if listing['price']:
            title_parts.append(f"{listing['price']} {listing['currency']}")
        
        if title_parts:
            listing['title'] = f"BMW M5 {' '.join(title_parts)}"
        else:
            listing['title'] = "BMW M5"
        
        return listing
    
    def _extract_currency(self, text: str) -> str:
        """Extract currency from text."""
        currency_match = re.search(r'(лв|€|\$|USD|EUR|BGN)', text)
        return currency_match.group(1) if currency_match else 'лв'


def test_intelligent_extractor():
    """Test the intelligent extractor with sample data."""
    extractor = IntelligentFieldExtractor()
    
    # Test with sample Bulgarian text
    sample_text = "BMW M5 Competition 2019 г. 113 000 км Черен Бензинов 625 к.с. Евро 6 4395 куб.см Автоматична Седан 109 999 лв"
    
    results = extractor.extract_fields_from_text(sample_text)
    
    print("=== INTELLIGENT EXTRACTION TEST ===")
    for field, value in results.items():
        print(f"{field}: {value}")
    
    return results


if __name__ == "__main__":
    test_intelligent_extractor()
