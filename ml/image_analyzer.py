"""Image analysis for car condition detection and feature extraction."""
import cv2
import numpy as np
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class CarImageAnalyzer:
    """Analyzes car images to detect condition, features, and anomalies."""
    
    def __init__(self):
        self.damage_detector = DamageDetector()
        self.feature_extractor = FeatureExtractor()
        self.quality_assessor = QualityAssessor()
    
    def analyze_car_image(self, image_path: str) -> Dict[str, Any]:
        """Analyze a car image and return comprehensive insights."""
        try:
            # Load image
            image = cv2.imread(image_path)
            if image is None:
                return {"error": "Could not load image"}
            
            # Run all analyses
            analysis = {
                "image_quality": self.quality_assessor.assess_quality(image),
                "damage_detection": self.damage_detector.detect_damage(image),
                "feature_extraction": self.feature_extractor.extract_features(image),
                "anomaly_detection": self._detect_anomalies(image),
                "overall_condition": "unknown"
            }
            
            # Calculate overall condition score
            analysis["overall_condition"] = self._calculate_condition_score(analysis)
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error analyzing image {image_path}: {e}")
            return {"error": str(e)}
    
    def _detect_anomalies(self, image: np.ndarray) -> Dict[str, Any]:
        """Detect anomalies that might indicate suspicious listings."""
        anomalies = {
            "suspicious_patterns": [],
            "image_manipulation": False,
            "stock_photo_detected": False,
            "confidence": 0.0
        }
        
        # Check for common stock photo patterns
        if self._is_likely_stock_photo(image):
            anomalies["stock_photo_detected"] = True
            anomalies["suspicious_patterns"].append("Stock photo detected")
        
        # Check for image manipulation
        if self._detect_image_manipulation(image):
            anomalies["image_manipulation"] = True
            anomalies["suspicious_patterns"].append("Image manipulation detected")
        
        # Calculate confidence
        anomaly_count = len(anomalies["suspicious_patterns"])
        anomalies["confidence"] = min(anomaly_count * 0.3, 1.0)
        
        return anomalies
    
    def _is_likely_stock_photo(self, image: np.ndarray) -> bool:
        """Detect if image is likely a stock photo."""
        # Check for professional photography patterns
        # - Perfect lighting
        # - Clean background
        # - Professional composition
        
        # Convert to HSV for better color analysis
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        
        # Check for very clean, uniform backgrounds
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 50, 150)
        edge_density = np.sum(edges > 0) / (image.shape[0] * image.shape[1])
        
        # Stock photos typically have very clean backgrounds (low edge density)
        return edge_density < 0.05
    
    def _detect_image_manipulation(self, image: np.ndarray) -> bool:
        """Detect potential image manipulation."""
        # Simple manipulation detection using edge analysis
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # Check for unusual edge patterns that might indicate cloning/editing
        edges = cv2.Canny(gray, 50, 150)
        
        # Look for repeated patterns (potential cloning)
        # This is a simplified approach - in production, use more sophisticated methods
        return False  # Placeholder
    
    def _calculate_condition_score(self, analysis: Dict[str, Any]) -> str:
        """Calculate overall condition based on all analyses."""
        quality_score = analysis.get("image_quality", {}).get("score", 0.5)
        damage_score = 1.0 - analysis.get("damage_detection", {}).get("damage_level", 0.0)
        anomaly_penalty = analysis.get("anomaly_detection", {}).get("confidence", 0.0)
        
        overall_score = (quality_score + damage_score) / 2 - anomaly_penalty
        overall_score = max(0.0, min(1.0, overall_score))
        
        if overall_score >= 0.8:
            return "excellent"
        elif overall_score >= 0.6:
            return "good"
        elif overall_score >= 0.4:
            return "fair"
        else:
            return "poor"


class DamageDetector:
    """Detects damage in car images."""
    
    def detect_damage(self, image: np.ndarray) -> Dict[str, Any]:
        """Detect various types of damage in the car image."""
        damage_info = {
            "damage_level": 0.0,
            "damage_types": [],
            "confidence": 0.0,
            "affected_areas": []
        }
        
        # Convert to grayscale for analysis
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # Detect scratches (linear features)
        scratches = self._detect_scratches(gray)
        if scratches > 0:
            damage_info["damage_types"].append("scratches")
            damage_info["damage_level"] += 0.2
        
        # Detect dents (circular/oval features)
        dents = self._detect_dents(gray)
        if dents > 0:
            damage_info["damage_types"].append("dents")
            damage_info["damage_level"] += 0.3
        
        # Detect rust (brownish discoloration)
        rust = self._detect_rust(image)
        if rust > 0:
            damage_info["damage_types"].append("rust")
            damage_info["damage_level"] += 0.4
        
        # Normalize damage level
        damage_info["damage_level"] = min(1.0, damage_info["damage_level"])
        damage_info["confidence"] = min(0.8, len(damage_info["damage_types"]) * 0.3)
        
        return damage_info
    
    def _detect_scratches(self, gray_image: np.ndarray) -> int:
        """Detect scratches using line detection."""
        # Use Hough line transform to detect linear features
        edges = cv2.Canny(gray_image, 50, 150)
        lines = cv2.HoughLinesP(edges, 1, np.pi/180, threshold=50, minLineLength=30, maxLineGap=10)
        
        if lines is not None:
            return len(lines)
        return 0
    
    def _detect_dents(self, gray_image: np.ndarray) -> int:
        """Detect dents using circle detection."""
        # Use Hough circle transform to detect circular features
        circles = cv2.HoughCircles(
            gray_image, cv2.HOUGH_GRADIENT, 1, 20,
            param1=50, param2=30, minRadius=10, maxRadius=100
        )
        
        if circles is not None:
            return len(circles[0])
        return 0
    
    def _detect_rust(self, image: np.ndarray) -> int:
        """Detect rust using color analysis."""
        # Convert to HSV for better color detection
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        
        # Define rust color range (brownish-red)
        lower_rust = np.array([0, 50, 50])
        upper_rust = np.array([20, 255, 255])
        
        # Create mask for rust colors
        rust_mask = cv2.inRange(hsv, lower_rust, upper_rust)
        
        # Count rust pixels
        rust_pixels = cv2.countNonZero(rust_mask)
        total_pixels = image.shape[0] * image.shape[1]
        
        # Return rust percentage
        return rust_pixels / total_pixels


class FeatureExtractor:
    """Extracts features and modifications from car images."""
    
    def extract_features(self, image: np.ndarray) -> Dict[str, Any]:
        """Extract car features and modifications."""
        features = {
            "modifications": [],
            "body_style": "unknown",
            "color": "unknown",
            "wheel_type": "unknown",
            "lighting": "standard"
        }
        
        # Extract dominant color
        features["color"] = self._extract_dominant_color(image)
        
        # Detect modifications
        features["modifications"] = self._detect_modifications(image)
        
        # Detect body style
        features["body_style"] = self._detect_body_style(image)
        
        return features
    
    def _extract_dominant_color(self, image: np.ndarray) -> str:
        """Extract the dominant color of the car."""
        # Convert to HSV for better color analysis
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        
        # Define color ranges
        color_ranges = {
            "black": ([0, 0, 0], [180, 255, 50]),
            "white": ([0, 0, 200], [180, 30, 255]),
            "red": ([0, 50, 50], [10, 255, 255]),
            "blue": ([100, 50, 50], [130, 255, 255]),
            "green": ([40, 50, 50], [80, 255, 255]),
            "yellow": ([20, 50, 50], [40, 255, 255]),
            "silver": ([0, 0, 100], [180, 30, 200])
        }
        
        max_pixels = 0
        dominant_color = "unknown"
        
        for color_name, (lower, upper) in color_ranges.items():
            mask = cv2.inRange(hsv, np.array(lower), np.array(upper))
            pixel_count = cv2.countNonZero(mask)
            
            if pixel_count > max_pixels:
                max_pixels = pixel_count
                dominant_color = color_name
        
        return dominant_color
    
    def _detect_modifications(self, image: np.ndarray) -> List[str]:
        """Detect common car modifications."""
        modifications = []
        
        # This is a simplified approach - in production, use more sophisticated methods
        # For now, we'll use basic pattern recognition
        
        # Check for aftermarket wheels (simplified)
        if self._has_aftermarket_wheels(image):
            modifications.append("aftermarket_wheels")
        
        # Check for body kit (simplified)
        if self._has_body_kit(image):
            modifications.append("body_kit")
        
        return modifications
    
    def _has_aftermarket_wheels(self, image: np.ndarray) -> bool:
        """Detect if car has aftermarket wheels."""
        # Simplified detection - look for unusual wheel patterns
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        circles = cv2.HoughCircles(
            gray, cv2.HOUGH_GRADIENT, 1, 20,
            param1=50, param2=30, minRadius=20, maxRadius=80
        )
        
        # If we find many circles (potential aftermarket wheels), flag it
        return circles is not None and len(circles[0]) > 4
    
    def _has_body_kit(self, image: np.ndarray) -> bool:
        """Detect if car has body kit modifications."""
        # Simplified detection - look for unusual body contours
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 50, 150)
        
        # Count edge density - body kits often have more complex edges
        edge_density = np.sum(edges > 0) / (image.shape[0] * image.shape[1])
        
        return edge_density > 0.15  # Threshold for body kit detection
    
    def _detect_body_style(self, image: np.ndarray) -> str:
        """Detect car body style (sedan, coupe, SUV, etc.)."""
        # Simplified detection based on image proportions
        height, width = image.shape[:2]
        aspect_ratio = width / height
        
        if aspect_ratio > 1.5:
            return "sedan"
        elif aspect_ratio > 1.2:
            return "coupe"
        else:
            return "suv"


class QualityAssessor:
    """Assesses image quality and photography standards."""
    
    def assess_quality(self, image: np.ndarray) -> Dict[str, Any]:
        """Assess the quality of the car image."""
        quality_info = {
            "score": 0.0,
            "resolution": "unknown",
            "lighting": "unknown",
            "composition": "unknown",
            "blur_level": 0.0
        }
        
        # Assess resolution
        height, width = image.shape[:2]
        total_pixels = height * width
        
        if total_pixels > 2000000:  # > 2MP
            quality_info["resolution"] = "high"
            quality_info["score"] += 0.3
        elif total_pixels > 500000:  # > 0.5MP
            quality_info["resolution"] = "medium"
            quality_info["score"] += 0.2
        else:
            quality_info["resolution"] = "low"
            quality_info["score"] += 0.1
        
        # Assess lighting
        lighting_score = self._assess_lighting(image)
        quality_info["lighting"] = lighting_score["quality"]
        quality_info["score"] += lighting_score["score"]
        
        # Assess blur
        blur_level = self._assess_blur(image)
        quality_info["blur_level"] = blur_level
        quality_info["score"] -= blur_level * 0.3
        
        # Normalize score
        quality_info["score"] = max(0.0, min(1.0, quality_info["score"]))
        
        return quality_info
    
    def _assess_lighting(self, image: np.ndarray) -> Dict[str, Any]:
        """Assess lighting quality in the image."""
        # Convert to grayscale
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # Calculate brightness and contrast
        brightness = np.mean(gray)
        contrast = np.std(gray)
        
        # Assess lighting quality
        if 100 <= brightness <= 180 and contrast > 50:
            return {"quality": "excellent", "score": 0.3}
        elif 80 <= brightness <= 200 and contrast > 30:
            return {"quality": "good", "score": 0.2}
        elif 60 <= brightness <= 220 and contrast > 20:
            return {"quality": "fair", "score": 0.1}
        else:
            return {"quality": "poor", "score": 0.0}
    
    def _assess_blur(self, image: np.ndarray) -> float:
        """Assess blur level in the image."""
        # Convert to grayscale
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # Use Laplacian variance to measure blur
        laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
        
        # Normalize blur level (higher variance = less blur)
        blur_level = max(0.0, 1.0 - (laplacian_var / 1000.0))
        
        return blur_level


# Example usage and testing
if __name__ == "__main__":
    analyzer = CarImageAnalyzer()
    
    # Test with a sample image
    test_image = "scraped_images/images/11758127825345248_tn.webp"
    if Path(test_image).exists():
        result = analyzer.analyze_car_image(test_image)
        print("Image Analysis Result:")
        print(f"Overall Condition: {result.get('overall_condition', 'unknown')}")
        print(f"Image Quality: {result.get('image_quality', {}).get('score', 0):.2f}")
        print(f"Damage Level: {result.get('damage_detection', {}).get('damage_level', 0):.2f}")
        print(f"Dominant Color: {result.get('feature_extraction', {}).get('color', 'unknown')}")
    else:
        print("No test image found")
