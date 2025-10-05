"""Quick debug script to inspect CarAdEnriched rows."""
from sqlalchemy.orm import Session

from db.database import SessionLocal
from db.models import CarAdEnriched


def main(limit: int = 10) -> None:
    db: Session = SessionLocal()
    try:
        total = db.query(CarAdEnriched).count()
        print(f"CarAdEnriched total rows: {total}")
        rows = (
            db.query(CarAdEnriched)
            .order_by(CarAdEnriched.id.desc())
            .limit(limit)
            .all()
        )
        for r in rows:
            print(
                f"id={r.id} raw_ad_id={r.raw_ad_id} color={r.detected_color} conf={r.detected_color_confidence}"
            )
    finally:
        db.close()


if __name__ == "__main__":
    main()


