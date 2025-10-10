"""Configuration for AutoEvolution scraper."""
import logging

BASE_URL = "https://www.autoevolution.com"

def setup_logging():
    """Sets up the global logger."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    return logging.getLogger(__name__)

logger = setup_logging()

