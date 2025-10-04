"""Car ad endpoints."""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc
from db.database import get_db
from db.models import CarAdRaw, CarAdEnriched
from api.schemas import CarAdResponse, CarAdEnrichedResponse

router = APIRouter()


@router.get("/", response_model=List[CarAdResponse])
async def list_car_ads(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    make: Optional[str] = None,
    model: Optional[str] = None,
    year: Optional[int] = None,
    is_active: bool = True,
    db: Session = Depends(get_db),
):
    """List car ads with optional filtering."""
    query = db.query(CarAdRaw).filter(CarAdRaw.is_active == is_active)
    
    if make:
        query = query.filter(CarAdRaw.make.ilike(f"%{make}%"))
    if model:
        query = query.filter(CarAdRaw.model.ilike(f"%{model}%"))
    if year:
        query = query.filter(CarAdRaw.year == year)
    
    ads = query.order_by(desc(CarAdRaw.scraped_at)).offset(skip).limit(limit).all()
    return ads


@router.get("/{ad_id}", response_model=CarAdResponse)
async def get_car_ad(ad_id: int, db: Session = Depends(get_db)):
    """Get a specific car ad by ID."""
    ad = db.query(CarAdRaw).filter(CarAdRaw.id == ad_id).first()
    if not ad:
        raise HTTPException(status_code=404, detail="Car ad not found")
    return ad


@router.get("/{ad_id}/enriched", response_model=CarAdEnrichedResponse)
async def get_enriched_car_ad(ad_id: int, db: Session = Depends(get_db)):
    """Get enriched data for a specific car ad."""
    enriched = db.query(CarAdEnriched).filter(CarAdEnriched.raw_ad_id == ad_id).first()
    if not enriched:
        raise HTTPException(status_code=404, detail="Enriched data not found for this ad")
    return enriched


@router.get("/stats/summary")
async def get_stats_summary(db: Session = Depends(get_db)):
    """Get summary statistics of car ads."""
    total_ads = db.query(CarAdRaw).count()
    active_ads = db.query(CarAdRaw).filter(CarAdRaw.is_active == True).count()
    processed_ads = db.query(CarAdRaw).filter(CarAdRaw.is_processed == True).count()
    enriched_ads = db.query(CarAdEnriched).count()
    
    return {
        "total_ads": total_ads,
        "active_ads": active_ads,
        "processed_ads": processed_ads,
        "enriched_ads": enriched_ads,
        "enrichment_rate": round(enriched_ads / total_ads * 100, 2) if total_ads > 0 else 0,
    }

