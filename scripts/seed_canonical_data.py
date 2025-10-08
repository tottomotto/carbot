import os
import sys
from pathlib import Path

# Add project root to the Python path
project_root = Path(__file__).resolve().parents[1]
sys.path.append(str(project_root))

from db import SessionLocal
from db.models import Manufacturer, Model, Variant

def get_or_create(session, model, defaults=None, **kwargs):
    """Gets an existing instance or creates a new one."""
    instance = session.query(model).filter_by(**kwargs).first()
    if instance:
        return instance, False
    else:
        params = {**kwargs, **(defaults or {})}
        instance = model(**params)
        session.add(instance)
        session.flush()
        return instance, True

def seed_data(db, manufacturer_name: str, model_name: str, variant_names: list[str]):
    """
    Seeds the database with a manufacturer, a model, and a list of variants for that model.
    """
    try:
        # 1. Get or create Manufacturer
        manufacturer, created = get_or_create(db, Manufacturer, name=manufacturer_name)
        if created:
            print(f"Created Manufacturer: '{manufacturer.name}'")
        else:
            print(f"Found existing Manufacturer: '{manufacturer.name}'")

        # 2. Get or create Model
        model, created = get_or_create(db, Model, name=model_name, manufacturer_id=manufacturer.id)
        if created:
            print(f"  - Created Model: '{model.name}'")
        else:
            print(f"  - Found existing Model: '{model.name}'")

        # 3. Get or create Variants
        for variant_name in variant_names:
            variant, created = get_or_create(db, Variant, name=variant_name, model_id=model.id)
            if created:
                print(f"    - Created Variant: '{variant.name}'")
            else:
                print(f"    - Found existing Variant: '{variant.name}'")
        
        db.commit()
        print("\nSuccessfully committed canonical data.")

    except Exception as e:
        print(f"\nAn error occurred: {e}")
        db.rollback()


def main():
    """Main function to seed the database with specific car data."""
    db = SessionLocal()
    try:
        print("--- Seeding BMW M5 Variants ---")
        seed_data(
            db=db,
            manufacturer_name="BMW",
            model_name="M5",
            variant_names=["Competition", "Base"]
        )
    finally:
        db.close()

if __name__ == "__main__":
    main()
