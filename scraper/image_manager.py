"""Advanced image management system with deduplication and cleanup."""
import os
import hashlib
import requests
from pathlib import Path
from typing import List, Optional, Dict, Any
from urllib.parse import urlparse
from sqlalchemy.orm import Session
from config.settings import settings
from db.models import CarAdRaw


class ImageManager:
    """Manages car images with deduplication, linking, and cleanup."""
    
    def __init__(self, base_dir: str = "scraped_images"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(exist_ok=True)
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': settings.scraper_user_agent,
        })
        
        # Create subdirectories
        self.images_dir = self.base_dir / "images"
        self.images_dir.mkdir(exist_ok=True)
        
        # Create metadata file for tracking
        self.metadata_file = self.base_dir / "image_metadata.json"
        self.metadata = self._load_metadata()
    
    def _load_metadata(self) -> Dict[str, Any]:
        """Load image metadata for tracking."""
        if self.metadata_file.exists():
            import json
            try:
                with open(self.metadata_file, 'r') as f:
                    return json.load(f)
            except:
                return {"images": {}, "ad_links": {}}
        return {"images": {}, "ad_links": {}}
    
    def _save_metadata(self):
        """Save image metadata."""
        import json
        with open(self.metadata_file, 'w') as f:
            json.dump(self.metadata, f, indent=2)
    
    def _get_image_hash(self, url: str) -> str:
        """Generate consistent hash for image URL."""
        return hashlib.md5(url.encode()).hexdigest()
    
    def _get_image_filename(self, url: str, source_id: str) -> str:
        """Generate filename for image."""
        parsed_url = urlparse(url)
        original_filename = os.path.basename(parsed_url.path)
        
        # If no extension, try to get from URL or default to jpg
        if not original_filename or '.' not in original_filename:
            # Try to get extension from URL
            if 'jpg' in url.lower() or 'jpeg' in url.lower():
                ext = '.jpg'
            elif 'png' in url.lower():
                ext = '.png'
            elif 'webp' in url.lower():
                ext = '.webp'
            else:
                ext = '.jpg'
            
            # Use source_id + hash for filename
            url_hash = self._get_image_hash(url)[:8]
            original_filename = f"{source_id}_{url_hash}{ext}"
        
        return original_filename
    
    def download_image(self, url: str, source_id: str) -> Optional[str]:
        """Download image with deduplication and return local path."""
        try:
            # Check if we already have this image
            image_hash = self._get_image_hash(url)
            if image_hash in self.metadata["images"]:
                existing_path = self.metadata["images"][image_hash]["local_path"]
                if os.path.exists(existing_path):
                    print(f"  ✓ Image already exists: {os.path.basename(existing_path)}")
                    return existing_path
                else:
                    # File was deleted, remove from metadata
                    del self.metadata["images"][image_hash]
            
            # Download the image
            response = self.session.get(url, timeout=30, stream=True)
            response.raise_for_status()
            
            # Check content type
            content_type = response.headers.get('content-type', '').lower()
            if not content_type.startswith('image/'):
                print(f"  ⚠️  Skipping non-image content: {url}")
                return None
            
            # Generate filename
            filename = self._get_image_filename(url, source_id)
            local_path = self.images_dir / filename
            
            # Save the image
            with open(local_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            # Update metadata
            self.metadata["images"][image_hash] = {
                "url": url,
                "local_path": str(local_path),
                "filename": filename,
                "source_id": source_id,
                "downloaded_at": str(Path(local_path).stat().st_mtime)
            }
            
            self._save_metadata()
            print(f"  ✓ Downloaded image: {filename}")
            return str(local_path)
            
        except Exception as e:
            print(f"  ✗ Error downloading image {url}: {e}")
            return None
    
    def download_images_for_ad(self, image_urls: List[str], source_id: str, max_images: int = 1) -> List[str]:
        """Download images for a car ad with deduplication."""
        downloaded_paths = []
        
        for i, url in enumerate(image_urls[:max_images]):
            if len(downloaded_paths) >= max_images:
                break
                
            local_path = self.download_image(url, source_id)
            if local_path:
                downloaded_paths.append(local_path)
        
        return downloaded_paths
    
    def link_images_to_ad(self, db: Session, ad_id: int, local_image_paths: List[str]):
        """Link downloaded images to car ad in database."""
        try:
            ad = db.query(CarAdRaw).filter(CarAdRaw.id == ad_id).first()
            if ad:
                ad.local_image_paths = local_image_paths
                db.commit()
                
                # Update metadata
                for path in local_image_paths:
                    image_hash = None
                    for hash_key, img_data in self.metadata["images"].items():
                        if img_data["local_path"] == path:
                            image_hash = hash_key
                            break
                    
                    if image_hash:
                        if "ad_links" not in self.metadata:
                            self.metadata["ad_links"] = {}
                        self.metadata["ad_links"][str(ad_id)] = {
                            "source_id": ad.source_id,
                            "image_paths": local_image_paths,
                            "linked_at": str(Path(path).stat().st_mtime)
                        }
                
                self._save_metadata()
                print(f"  ✓ Linked {len(local_image_paths)} images to ad {ad_id}")
        except Exception as e:
            print(f"  ✗ Error linking images to ad {ad_id}: {e}")
    
    def cleanup_orphaned_images(self, db: Session):
        """Remove images that are no longer linked to any car ads."""
        try:
            # Get all current ad image paths
            current_image_paths = set()
            ads = db.query(CarAdRaw).all()
            for ad in ads:
                if ad.local_image_paths:
                    current_image_paths.update(ad.local_image_paths)
            
            # Find orphaned images
            orphaned_count = 0
            for image_hash, img_data in list(self.metadata["images"].items()):
                local_path = img_data["local_path"]
                if local_path not in current_image_paths:
                    # This image is orphaned
                    if os.path.exists(local_path):
                        os.remove(local_path)
                        print(f"  🗑️  Removed orphaned image: {os.path.basename(local_path)}")
                        orphaned_count += 1
                    
                    # Remove from metadata
                    del self.metadata["images"][image_hash]
            
            # Clean up ad_links metadata
            current_ad_ids = {str(ad.id) for ad in ads}
            for ad_id in list(self.metadata.get("ad_links", {}).keys()):
                if ad_id not in current_ad_ids:
                    del self.metadata["ad_links"][ad_id]
            
            self._save_metadata()
            print(f"  ✓ Cleaned up {orphaned_count} orphaned images")
            
        except Exception as e:
            print(f"  ✗ Error during cleanup: {e}")
    
    def get_image_stats(self) -> Dict[str, Any]:
        """Get statistics about stored images."""
        total_images = len(self.metadata["images"])
        total_size = 0
        for img_data in self.metadata["images"].values():
            local_path = img_data["local_path"]
            if os.path.exists(local_path):
                total_size += os.path.getsize(local_path)
        
        return {
            "total_images": total_images,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "linked_ads": len(self.metadata.get("ad_links", {})),
        }
    
    def close(self):
        """Close the session."""
        self.session.close()


def download_and_link_images(image_urls: List[str], source_id: str, ad_id: int, db: Session, max_images: int = 1) -> List[str]:
    """Convenience function to download and link images."""
    manager = ImageManager()
    try:
        downloaded_paths = manager.download_images_for_ad(image_urls, source_id, max_images)
        if downloaded_paths:
            manager.link_images_to_ad(db, ad_id, downloaded_paths)
        return downloaded_paths
    finally:
        manager.close()


if __name__ == "__main__":
    # Test the image manager
    manager = ImageManager()
    stats = manager.get_image_stats()
    print(f"Image stats: {stats}")
    manager.close()
