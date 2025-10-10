"""Clear all car ads from database to start fresh."""
import sys
from pathlib import Path
import os

# Add project root to the Python path
project_root = Path(__file__).resolve().parents[1]
sys.path.append(str(project_root))

from db.database import engine
from sqlalchemy import text

def clear_database():
    """Drops all tables in the database using CASCADE."""
    print("--- Clearing Database ---")
    try:
        with engine.connect() as connection:
            connection.execute(text("DROP SCHEMA public CASCADE;"))
            connection.execute(text("CREATE SCHEMA public;"))
            print("Successfully dropped and recreated public schema.")
            connection.commit()
    except Exception as e:
        print(f"An error occurred while clearing the database: {e}")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Drop all tables in the database.")
    parser.add_argument("--confirm", action="store_true", help="Confirm the operation.")
    args = parser.parse_args()

    if args.confirm:
        clear_database()
    else:
        print("Operation cancelled. Please run with --confirm to proceed.")
