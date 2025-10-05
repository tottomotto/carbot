"""Anomaly detection for suspicious car listings."""
import numpy as np
import pandas as pd
from typing import Dict, List, Any, Optional, Tuple
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
import logging

logger = logging.getLogger(__name__)


class CarAnomalyDetector:
    """Detects anomalies and suspicious patterns in car listings."""
    
    def __init__(self):
        self.isolation_forest = IsolationForest(contamination=0.1, random_state=42)
        self.scaler = StandardScaler()
        self.is_trained = False
        self.feature_columns = []
    
    def detect_anomalies(self, car_ads: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Detect anomalies in a list of car ads."""
        if not car_ads:
            return []
        
        anomalies = []
        
        for i, ad in enumerate(car_ads):
            anomaly_score = self._analyze_single_listing(ad, car_ads)
            if anomaly_score['is_anomaly']:
                anomalies.append({
                    'ad_id': ad.get('id', i),
                    'source_id': ad.get('source_id', 'unknown'),
                    'anomaly_score': anomaly_score['score'],
                    'anomaly_reasons': anomaly_score['reasons'],
                    'confidence': anomaly_score['confidence']
                })
        
        return anomalies
    
    def _analyze_single_listing(self, ad: Dict[str, Any], all_ads: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze a single listing for anomalies."""
        reasons = []
        anomaly_score = 0.0
        
        # Price anomalies
        price_anomaly = self._detect_price_anomaly(ad, all_ads)
        if price_anomaly['is_anomaly']:
            reasons.append(price_anomaly['reason'])
            anomaly_score += price_anomaly['score']
        
        # Mileage anomalies
        mileage_anomaly = self._detect_mileage_anomaly(ad, all_ads)
        if mileage_anomaly['is_anomaly']:
            reasons.append(mileage_anomaly['reason'])
            anomaly_score += mileage_anomaly['score']
        
        # Year anomalies
        year_anomaly = self._detect_year_anomaly(ad, all_ads)
        if year_anomaly['is_anomaly']:
            reasons.append(year_anomaly['reason'])
            anomaly_score += year_anomaly['score']
        
        # Dealer anomalies
        dealer_anomaly = self._detect_dealer_anomaly(ad, all_ads)
        if dealer_anomaly['is_anomaly']:
            reasons.append(dealer_anomaly['reason'])
            anomaly_score += dealer_anomaly['score']
        
        # Image anomalies
        image_anomaly = self._detect_image_anomaly(ad)
        if image_anomaly['is_anomaly']:
            reasons.append(image_anomaly['reason'])
            anomaly_score += image_anomaly['score']
        
        # Text anomalies
        text_anomaly = self._detect_text_anomaly(ad)
        if text_anomaly['is_anomaly']:
            reasons.append(text_anomaly['reason'])
            anomaly_score += text_anomaly['score']
        
        return {
            'is_anomaly': len(reasons) > 0,
            'score': min(1.0, anomaly_score),
            'reasons': reasons,
            'confidence': min(0.9, len(reasons) * 0.2)
        }
    
    def _detect_price_anomaly(self, ad: Dict[str, Any], all_ads: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Detect price-related anomalies."""
        price = ad.get('price')
        if not price:
            return {'is_anomaly': False}
        
        # Get prices for similar cars
        similar_prices = []
        for other_ad in all_ads:
            if (other_ad.get('year') == ad.get('year') and 
                other_ad.get('make') == ad.get('make') and
                other_ad.get('model') == ad.get('model') and
                other_ad.get('price')):
                similar_prices.append(other_ad['price'])
        
        if len(similar_prices) < 3:
            return {'is_anomaly': False}
        
        similar_prices = np.array(similar_prices)
        mean_price = np.mean(similar_prices)
        std_price = np.std(similar_prices)
        
        # Check if price is significantly different
        z_score = abs(price - mean_price) / std_price if std_price > 0 else 0
        
        if z_score > 3:
            return {
                'is_anomaly': True,
                'score': min(0.4, z_score * 0.1),
                'reason': f"Price {z_score:.1f} standard deviations from similar cars"
            }
        elif z_score > 2:
            return {
                'is_anomaly': True,
                'score': min(0.2, z_score * 0.05),
                'reason': f"Price {z_score:.1f} standard deviations from similar cars"
            }
        
        return {'is_anomaly': False}
    
    def _detect_mileage_anomaly(self, ad: Dict[str, Any], all_ads: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Detect mileage-related anomalies."""
        mileage = ad.get('mileage')
        year = ad.get('year')
        
        if not mileage or not year:
            return {'is_anomaly': False}
        
        # Calculate expected mileage (average 15,000 km/year)
        age = 2024 - year
        expected_mileage = age * 15000
        
        # Check for unrealistic mileage
        if mileage < 1000 and age > 1:
            return {
                'is_anomaly': True,
                'score': 0.3,
                'reason': f"Extremely low mileage ({mileage:,} km) for {age}-year-old car"
            }
        
        if mileage > expected_mileage * 3:
            return {
                'is_anomaly': True,
                'score': 0.2,
                'reason': f"Very high mileage ({mileage:,} km) for {age}-year-old car"
            }
        
        return {'is_anomaly': False}
    
    def _detect_year_anomaly(self, ad: Dict[str, Any], all_ads: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Detect year-related anomalies."""
        year = ad.get('year')
        if not year:
            return {'is_anomaly': False}
        
        # Check for future years
        if year > 2024:
            return {
                'is_anomaly': True,
                'score': 0.5,
                'reason': f"Future year ({year}) - likely data error"
            }
        
        # Check for very old cars in modern listings
        if year < 1990:
            return {
                'is_anomaly': True,
                'score': 0.2,
                'reason': f"Very old car ({year}) in modern listing"
            }
        
        return {'is_anomaly': False}
    
    def _detect_dealer_anomaly(self, ad: Dict[str, Any], all_ads: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Detect dealer-related anomalies."""
        dealer_name = ad.get('dealer_name')
        dealer_type = ad.get('dealer_type')
        
        if not dealer_name and dealer_type == 'dealer':
            return {
                'is_anomaly': True,
                'score': 0.1,
                'reason': "Dealer listing without dealer name"
            }
        
        # Check for suspicious dealer names
        suspicious_patterns = ['test', 'demo', 'fake', 'scam', 'fraud']
        if dealer_name:
            dealer_lower = dealer_name.lower()
            for pattern in suspicious_patterns:
                if pattern in dealer_lower:
                    return {
                        'is_anomaly': True,
                        'score': 0.4,
                        'reason': f"Suspicious dealer name: {dealer_name}"
                    }
        
        return {'is_anomaly': False}
    
    def _detect_image_anomaly(self, ad: Dict[str, Any]) -> Dict[str, Any]:
        """Detect image-related anomalies."""
        image_urls = ad.get('image_urls', [])
        local_images = ad.get('local_image_paths', [])
        
        # No images
        if not image_urls and not local_images:
            return {
                'is_anomaly': True,
                'score': 0.2,
                'reason': "No images provided"
            }
        
        # Too many images (potential spam)
        if len(image_urls) > 20:
            return {
                'is_anomaly': True,
                'score': 0.1,
                'reason': f"Unusually high number of images ({len(image_urls)})"
            }
        
        return {'is_anomaly': False}
    
    def _detect_text_anomaly(self, ad: Dict[str, Any]) -> Dict[str, Any]:
        """Detect text-related anomalies."""
        title = ad.get('title', '')
        raw_data = ad.get('raw_data', {})
        text_content = raw_data.get('text_content', '')
        
        # Check for suspicious keywords
        suspicious_keywords = [
            'urgent', 'quick sale', 'must sell', 'cash only',
            'no questions', 'as is', 'no warranty', 'final price'
        ]
        
        text_lower = (title + ' ' + text_content).lower()
        found_keywords = [kw for kw in suspicious_keywords if kw in text_lower]
        
        if len(found_keywords) > 2:
            return {
                'is_anomaly': True,
                'score': 0.3,
                'reason': f"Suspicious keywords: {', '.join(found_keywords)}"
            }
        
        # Check for excessive repetition
        words = text_content.split()
        if len(words) > 100:
            word_counts = {}
            for word in words:
                word_counts[word] = word_counts.get(word, 0) + 1
            
            max_repetition = max(word_counts.values()) if word_counts else 0
            if max_repetition > len(words) * 0.1:
                return {
                    'is_anomaly': True,
                    'score': 0.2,
                    'reason': "Excessive word repetition in description"
                }
        
        return {'is_anomaly': False}
    
    def get_anomaly_summary(self, anomalies: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Get summary of detected anomalies."""
        if not anomalies:
            return {
                "total_anomalies": 0,
                "anomaly_rate": 0.0,
                "common_reasons": [],
                "risk_level": "low"
            }
        
        # Count anomaly reasons
        reason_counts = {}
        for anomaly in anomalies:
            for reason in anomaly['anomaly_reasons']:
                reason_counts[reason] = reason_counts.get(reason, 0) + 1
        
        # Sort by frequency
        common_reasons = sorted(reason_counts.items(), key=lambda x: x[1], reverse=True)
        
        # Calculate risk level
        avg_score = np.mean([a['anomaly_score'] for a in anomalies])
        if avg_score > 0.5:
            risk_level = "high"
        elif avg_score > 0.3:
            risk_level = "medium"
        else:
            risk_level = "low"
        
        return {
            "total_anomalies": len(anomalies),
            "anomaly_rate": len(anomalies) / 100,  # Assuming 100 total listings
            "common_reasons": common_reasons[:5],
            "risk_level": risk_level,
            "average_anomaly_score": float(avg_score)
        }


# Example usage
if __name__ == "__main__":
    detector = CarAnomalyDetector()
    
    # Sample car ads
    sample_ads = [
        {
            "id": 1,
            "source_id": "test_1",
            "year": 2020,
            "make": "BMW",
            "model": "M5",
            "price": 80000,
            "mileage": 50000,
            "dealer_name": "BMW Dealer",
            "dealer_type": "dealer",
            "title": "BMW M5 2020 - Excellent Condition",
            "image_urls": ["image1.jpg", "image2.jpg"]
        },
        {
            "id": 2,
            "source_id": "test_2", 
            "year": 2020,
            "make": "BMW",
            "model": "M5",
            "price": 20000,  # Suspiciously low price
            "mileage": 1000,  # Suspiciously low mileage
            "dealer_name": "Quick Sale Motors",
            "dealer_type": "dealer",
            "title": "URGENT SALE - BMW M5 - CASH ONLY - NO QUESTIONS",
            "image_urls": []
        }
    ]
    
    # Detect anomalies
    anomalies = detector.detect_anomalies(sample_ads)
    print("Detected anomalies:", anomalies)
    
    # Get summary
    summary = detector.get_anomaly_summary(anomalies)
    print("Anomaly summary:", summary)
