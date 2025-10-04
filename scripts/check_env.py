"""Check environment configuration."""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from config.settings import settings
    
    print("✓ Environment configuration loaded successfully!")
    print("\nConfiguration:")
    print(f"  Database Host: {settings.database_host}")
    print(f"  Database Port: {settings.database_port}")
    print(f"  Database Name: {settings.database_name}")
    print(f"  Database User: {settings.database_user}")
    print(f"  API Host: {settings.api_host}")
    print(f"  API Port: {settings.api_port}")
    print(f"  Debug Mode: {settings.debug}")
    
except Exception as e:
    print(f"✗ Error loading configuration: {e}")
    sys.exit(1)

