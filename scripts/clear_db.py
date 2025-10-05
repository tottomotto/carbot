"""Clear all car ads from database to start fresh."""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from db.database import engine


def clear_car_ads():
    """Clear all car ads from the database."""
    print("Clearing all car ads from database...")
    
    try:
        with engine.connect() as conn:
            # Delete in order due to foreign key constraints
            conn.execute(text("DELETE FROM car_ads_enriched"))
            print("✓ Cleared car_ads_enriched table")
            
            conn.execute(text("DELETE FROM car_ads_raw"))
            print("✓ Cleared car_ads_raw table")
            
            conn.execute(text("DELETE FROM official_car_data"))
            print("✓ Cleared official_car_data table")
            
            conn.commit()
            print("✓ Database cleared successfully!")
            
    except Exception as e:
        print(f"✗ Error clearing database: {e}")
        return False
    
    return True


if __name__ == "__main__":
    success = clear_car_ads()
    sys.exit(0 if success else 1)
