"""Main scraper runner."""
import json
import time
import random
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime
from sqlalchemy.orm import Session

from config.settings import settings
from db.database import SessionLocal
from db.models import CarAdRaw


class ScraperRunner:
    """Main scraper class for running configured scrape jobs."""
    
    def __init__(self, config_path: str):
        """Initialize scraper with configuration."""
        self.config_path = Path(config_path)
        self.config = self._load_config()
        self.db: Session = SessionLocal()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load scraper configuration from JSON file."""
        with open(self.config_path, 'r') as f:
            return json.load(f)
    
    def _get_delay(self) -> float:
        """Get random delay between requests."""
        return random.uniform(
            settings.scraper_delay_min,
            settings.scraper_delay_max
        )
    
    def scrape(self) -> List[Dict[str, Any]]:
        """Run the scraper based on configuration."""
        print(f"Starting scrape job: {self.config.get('name')}")
        print(f"Target: {self.config.get('make')} {self.config.get('model')}")
        print(f"Year range: {self.config.get('year_from')} - {self.config.get('year_to', 'present')}")
        
        # TODO: Implement actual scraping logic
        # This is a placeholder structure
        scraped_ads = []
        
        for site_config in self.config.get('sites', []):
            print(f"\nScraping {site_config['name']}...")
            site_ads = self._scrape_site(site_config)
            scraped_ads.extend(site_ads)
            
            # Delay between sites
            time.sleep(self._get_delay())
        
        print(f"\nTotal ads scraped: {len(scraped_ads)}")
        return scraped_ads
    
    def _scrape_site(self, site_config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Scrape a specific site."""
        site_name = site_config.get('name', 'unknown')
        base_url = site_config.get('base_url')
        
        print(f"  URL: {base_url}")
        print(f"  Method: {site_config.get('method', 'GET')}")
        
        # Import and use site-specific scrapers
        if site_name == 'mobile_bg':
            from scraper.sites.mobile_bg import scrape_mobile_bg_bmw_m5
            return scrape_mobile_bg_bmw_m5(base_url)
        else:
            print(f"  ⚠️  No scraper implemented for site: {site_name}")
            return []
    
    def save_to_db(self, ads: List[Dict[str, Any]]) -> int:
        """Save scraped ads to database."""
        saved_count = 0
        
        for ad_data in ads:
            try:
                # Check if ad already exists
                existing = self.db.query(CarAdRaw).filter(
                    CarAdRaw.source_site == ad_data['source_site'],
                    CarAdRaw.source_id == ad_data['source_id']
                ).first()
                
                if existing:
                    print(f"Ad already exists: {ad_data['source_id']}")
                    continue
                
                # Download images if available
                downloaded_images = []
                if ad_data.get('image_urls'):
                    from scraper.image_manager import download_and_link_images
                    # We'll link images after saving the ad
                
                # Create new ad record
                car_ad = CarAdRaw(
                    source_site=ad_data['source_site'],
                    source_id=ad_data['source_id'],
                    source_url=ad_data['source_url'],
                    raw_data=ad_data.get('raw_data', {}),
                    title=ad_data.get('title'),
                    price=ad_data.get('price'),
                    currency=ad_data.get('currency'),
                    year=ad_data.get('year'),
                    make=ad_data.get('make'),
                    model=ad_data.get('model'),
                    mileage=ad_data.get('mileage'),
                    location=ad_data.get('location'),
                    dealer_name=ad_data.get('dealer_name'),
                    dealer_type=ad_data.get('dealer_type'),
                    fuel_type=ad_data.get('fuel_type'),
                    transmission=ad_data.get('transmission'),
                    body_type=ad_data.get('body_type'),
                    color=ad_data.get('color'),
                    engine_power=ad_data.get('engine_power'),
                    engine_displacement=ad_data.get('engine_displacement'),
                    image_urls=ad_data.get('image_urls', []),
                    scraped_at=datetime.utcnow(),
                )
                
                self.db.add(car_ad)
                self.db.commit()
                
                # Download and link images after saving the ad
                if ad_data.get('image_urls'):
                    from scraper.image_manager import download_and_link_images
                    downloaded_images = download_and_link_images(
                        ad_data['image_urls'], 
                        ad_data['source_id'], 
                        car_ad.id, 
                        self.db, 
                        max_images=1
                    )
                
                saved_count += 1
                
            except Exception as e:
                print(f"Error saving ad {ad_data.get('source_id')}: {e}")
                self.db.rollback()
        
        print(f"Saved {saved_count} new ads to database")
        return saved_count
    
    def close(self):
        """Close database connection."""
        self.db.close()


def main():
    """Main entry point for scraper."""
    # Example usage
    config_file = "scraper/configs/bmw_m5_2019plus.json"
    
    if not Path(config_file).exists():
        print(f"Config file not found: {config_file}")
        print("Please create a scraper configuration file first.")
        return
    
    scraper = ScraperRunner(config_file)
    try:
        ads = scraper.scrape()
        scraper.save_to_db(ads)
    finally:
        scraper.close()


if __name__ == "__main__":
    main()

