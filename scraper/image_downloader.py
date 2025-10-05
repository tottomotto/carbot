"""Image downloading functionality for scraped car ads."""
import os
import requests
from pathlib import Path
from typing import List, Optional
from urllib.parse import urlparse
import hashlib
from config.settings import settings


class ImageDownloader:
    """Downloads and stores car images locally."""
    
    def __init__(self, base_dir: str = "scraped_images"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(exist_ok=True)
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': settings.scraper_user_agent,
        })
    
    def download_image(self, url: str, source_id: str) -> Optional[str]:
        """Download a single image and return the local path."""
        try:
            # Create filename from URL and source_id
            parsed_url = urlparse(url)
            filename = os.path.basename(parsed_url.path)
            
            # If no filename, create one from URL hash
            if not filename or '.' not in filename:
                url_hash = hashlib.md5(url.encode()).hexdigest()[:8]
                filename = f"{source_id}_{url_hash}.jpg"
            
            # Ensure we have a valid extension
            if not any(filename.lower().endswith(ext) for ext in ['.jpg', '.jpeg', '.png', '.webp']):
                filename += '.jpg'
            
            # Create subdirectory for this source_id
            subdir = self.base_dir / source_id
            subdir.mkdir(exist_ok=True)
            
            local_path = subdir / filename
            
            # Skip if already exists
            if local_path.exists():
                return str(local_path)
            
            # Download the image
            response = self.session.get(url, timeout=30, stream=True)
            response.raise_for_status()
            
            # Check content type
            content_type = response.headers.get('content-type', '').lower()
            if not content_type.startswith('image/'):
                print(f"  ⚠️  Skipping non-image content: {url}")
                return None
            
            # Save the image
            with open(local_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            print(f"  ✓ Downloaded image: {filename}")
            return str(local_path)
            
        except Exception as e:
            print(f"  ✗ Error downloading image {url}: {e}")
            return None
    
    def download_images(self, image_urls: List[str], source_id: str, max_images: int = 3) -> List[str]:
        """Download multiple images for a car ad."""
        downloaded_paths = []
        
        for i, url in enumerate(image_urls[:max_images]):
            if len(downloaded_paths) >= max_images:
                break
                
            local_path = self.download_image(url, source_id)
            if local_path:
                downloaded_paths.append(local_path)
        
        return downloaded_paths
    
    def close(self):
        """Close the session."""
        self.session.close()


def download_car_images(image_urls: List[str], source_id: str, max_images: int = 3) -> List[str]:
    """Convenience function to download car images."""
    downloader = ImageDownloader()
    try:
        return downloader.download_images(image_urls, source_id, max_images)
    finally:
        downloader.close()
