"""ML-powered API endpoints for car analysis."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Dict, Any
import logging

from db.database import get_db
from db.models import CarAdRaw
from ml.image_analyzer import CarImageAnalyzer
from ml.price_predictor import CarPricePredictor
from ml.anomaly_detector import CarAnomalyDetector

logger = logging.getLogger(__name__)
router = APIRouter()

# Initialize ML components
image_analyzer = CarImageAnalyzer()
price_predictor = CarPricePredictor()
anomaly_detector = CarAnomalyDetector()


@router.get("/analyze-image/{ad_id}")
async def analyze_car_image(ad_id: int, db: Session = Depends(get_db)):
    """Analyze car image for condition, damage, and features."""
    try:
        # Get car ad
        car_ad = db.query(CarAdRaw).filter(CarAdRaw.id == ad_id).first()
        if not car_ad:
            raise HTTPException(status_code=404, detail="Car ad not found")
        
        # Check if car has local images
        if not car_ad.local_image_paths:
            return {
                "ad_id": ad_id,
                "error": "No local images available for analysis",
                "suggestion": "Run scraper to download images first"
            }
        
        # Analyze first image
        image_path = car_ad.local_image_paths[0]
        analysis = image_analyzer.analyze_car_image(image_path)
        
        return {
            "ad_id": ad_id,
            "source_id": car_ad.source_id,
            "image_path": image_path,
            "analysis": analysis
        }
        
    except Exception as e:
        logger.error(f"Error analyzing image for ad {ad_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/predict-price/{ad_id}")
async def predict_car_price(ad_id: int, db: Session = Depends(get_db)):
    """Predict fair market price for a car."""
    try:
        # Get car ad
        car_ad = db.query(CarAdRaw).filter(CarAdRaw.id == ad_id).first()
        if not car_ad:
            raise HTTPException(status_code=404, detail="Car ad not found")
        
        # Prepare car data for prediction
        car_data = {
            "year": car_ad.year,
            "mileage": car_ad.mileage,
            "engine_power": car_ad.engine_power,
            "engine_displacement": car_ad.engine_displacement,
            "fuel_type": car_ad.fuel_type,
            "transmission": car_ad.transmission,
            "body_type": car_ad.body_type,
            "color": car_ad.color,
            "dealer_type": car_ad.dealer_type
        }
        
        # Predict price
        prediction = price_predictor.predict_price(car_data)
        
        return {
            "ad_id": ad_id,
            "source_id": car_ad.source_id,
            "current_price": car_ad.price,
            "predicted_price": prediction.get("predicted_price"),
            "confidence": prediction.get("confidence"),
            "price_difference": car_ad.price - prediction.get("predicted_price", 0) if car_ad.price else None,
            "is_good_deal": car_ad.price < prediction.get("predicted_price", 0) * 0.9 if car_ad.price else None
        }
        
    except Exception as e:
        logger.error(f"Error predicting price for ad {ad_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/detect-anomalies")
async def detect_listing_anomalies(limit: int = 50, db: Session = Depends(get_db)):
    """Detect anomalies and suspicious listings."""
    try:
        # Get recent car ads
        car_ads = db.query(CarAdRaw).filter(CarAdRaw.is_active == True).limit(limit).all()
        
        if not car_ads:
            return {"message": "No car ads found"}
        
        # Convert to dict format
        ads_data = []
        for ad in car_ads:
            ad_dict = {
                "id": ad.id,
                "source_id": ad.source_id,
                "year": ad.year,
                "make": ad.make,
                "model": ad.model,
                "price": ad.price,
                "mileage": ad.mileage,
                "dealer_name": ad.dealer_name,
                "dealer_type": ad.dealer_type,
                "title": ad.title,
                "image_urls": ad.image_urls or [],
                "local_image_paths": ad.local_image_paths or [],
                "raw_data": ad.raw_data or {}
            }
            ads_data.append(ad_dict)
        
        # Detect anomalies
        anomalies = anomaly_detector.detect_anomalies(ads_data)
        summary = anomaly_detector.get_anomaly_summary(anomalies)
        
        return {
            "total_listings_analyzed": len(ads_data),
            "anomalies_detected": len(anomalies),
            "summary": summary,
            "anomalies": anomalies
        }
        
    except Exception as e:
        logger.error(f"Error detecting anomalies: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/train-price-model")
async def train_price_model(db: Session = Depends(get_db)):
    """Train the price prediction model with current data."""
    try:
        # Get all car ads with prices
        car_ads = db.query(CarAdRaw).filter(
            CarAdRaw.is_active == True,
            CarAdRaw.price.isnot(None)
        ).all()
        
        if len(car_ads) < 10:
            return {
                "error": "Insufficient data for training",
                "required": 10,
                "available": len(car_ads),
                "suggestion": "Scrape more car ads with price data"
            }
        
        # Convert to dict format
        ads_data = []
        for ad in car_ads:
            ad_dict = {
                "year": ad.year,
                "mileage": ad.mileage,
                "engine_power": ad.engine_power,
                "engine_displacement": ad.engine_displacement,
                "fuel_type": ad.fuel_type,
                "transmission": ad.transmission,
                "body_type": ad.body_type,
                "color": ad.color,
                "dealer_type": ad.dealer_type,
                "price": ad.price
            }
            ads_data.append(ad_dict)
        
        # Train model
        training_result = price_predictor.train_model(ads_data)
        
        return {
            "status": "success",
            "training_result": training_result,
            "model_info": price_predictor.get_model_info()
        }
        
    except Exception as e:
        logger.error(f"Error training price model: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/market-analysis")
async def get_market_analysis(limit: int = 100, db: Session = Depends(get_db)):
    """Get comprehensive market analysis."""
    try:
        # Get car ads
        car_ads = db.query(CarAdRaw).filter(CarAdRaw.is_active == True).limit(limit).all()
        
        if not car_ads:
            return {"error": "No car ads found"}
        
        # Convert to dict format
        ads_data = []
        for ad in car_ads:
            ad_dict = {
                "year": ad.year,
                "mileage": ad.mileage,
                "engine_power": ad.engine_power,
                "engine_displacement": ad.engine_displacement,
                "fuel_type": ad.fuel_type,
                "transmission": ad.transmission,
                "body_type": ad.body_type,
                "color": ad.color,
                "dealer_type": ad.dealer_type,
                "price": ad.price
            }
            ads_data.append(ad_dict)
        
        # Analyze market
        market_analysis = price_predictor.analyze_market(ads_data)
        
        return {
            "total_listings": len(ads_data),
            "analysis": market_analysis,
            "model_trained": price_predictor.is_trained
        }
        
    except Exception as e:
        logger.error(f"Error analyzing market: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/ml-status")
async def get_ml_status():
    """Get status of ML components."""
    return {
        "image_analyzer": {
            "status": "ready",
            "features": ["damage_detection", "feature_extraction", "quality_assessment", "anomaly_detection"]
        },
        "price_predictor": {
            "status": "ready" if price_predictor.is_trained else "needs_training",
            "trained": price_predictor.is_trained,
            "model_info": price_predictor.get_model_info()
        },
        "anomaly_detector": {
            "status": "ready",
            "features": ["price_anomalies", "mileage_anomalies", "dealer_anomalies", "text_anomalies"]
        }
    }
