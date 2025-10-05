"""Price prediction model for car market analysis."""
import numpy as np
import pandas as pd
from typing import Dict, List, Any, Optional, Tuple
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.metrics import mean_absolute_error, r2_score
import joblib
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class CarPricePredictor:
    """ML model for predicting car prices and market analysis."""
    
    def __init__(self, model_path: str = "ml/models/price_predictor.pkl"):
        self.model_path = Path(model_path)
        self.model = None
        self.label_encoders = {}
        self.scaler = StandardScaler()
        self.feature_columns = []
        self.is_trained = False
        
        # Load existing model if available
        self.load_model()
    
    def prepare_training_data(self, car_ads: List[Dict[str, Any]]) -> Tuple[np.ndarray, np.ndarray]:
        """Prepare training data from car ads."""
        if not car_ads:
            return np.array([]), np.array([])
        
        # Convert to DataFrame
        df = pd.DataFrame(car_ads)
        
        # Filter out ads without prices
        df = df.dropna(subset=['price'])
        
        if len(df) == 0:
            return np.array([]), np.array([])
        
        # Define features for prediction
        feature_columns = [
            'year', 'mileage', 'engine_power', 'engine_displacement',
            'fuel_type', 'transmission', 'body_type', 'color', 'dealer_type'
        ]
        
        # Prepare features
        X = df[feature_columns].copy()
        y = df['price'].values
        
        # Handle missing values
        X = X.fillna({
            'year': X['year'].median() if not X['year'].isna().all() else 2020,
            'mileage': X['mileage'].median() if not X['mileage'].isna().all() else 50000,
            'engine_power': X['engine_power'].median() if not X['engine_power'].isna().all() else 300,
            'engine_displacement': X['engine_displacement'].median() if not X['engine_displacement'].isna().all() else 3.0,
            'fuel_type': 'unknown',
            'transmission': 'unknown',
            'body_type': 'unknown',
            'color': 'unknown',
            'dealer_type': 'unknown'
        })
        
        # Encode categorical variables
        categorical_columns = ['fuel_type', 'transmission', 'body_type', 'color', 'dealer_type']
        for col in categorical_columns:
            if col not in self.label_encoders:
                self.label_encoders[col] = LabelEncoder()
                X[col] = self.label_encoders[col].fit_transform(X[col].astype(str))
            else:
                # Handle unseen categories
                X[col] = X[col].astype(str)
                X[col] = X[col].apply(lambda x: x if x in self.label_encoders[col].classes_ else 'unknown')
                X[col] = self.label_encoders[col].transform(X[col])
        
        self.feature_columns = feature_columns
        
        return X.values, y
    
    def train_model(self, car_ads: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Train the price prediction model."""
        X, y = self.prepare_training_data(car_ads)
        
        if len(X) == 0:
            return {"error": "No training data available"}
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42
        )
        
        # Scale features
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_test_scaled = self.scaler.transform(X_test)
        
        # Train model
        self.model = RandomForestRegressor(
            n_estimators=100,
            max_depth=10,
            random_state=42,
            n_jobs=-1
        )
        
        self.model.fit(X_train_scaled, y_train)
        
        # Evaluate model
        y_pred = self.model.predict(X_test_scaled)
        mae = mean_absolute_error(y_test, y_pred)
        r2 = r2_score(y_test, y_pred)
        
        self.is_trained = True
        
        # Save model
        self.save_model()
        
        return {
            "status": "trained",
            "training_samples": len(X_train),
            "test_samples": len(X_test),
            "mae": mae,
            "r2_score": r2,
            "feature_importance": dict(zip(
                self.feature_columns,
                self.model.feature_importances_
            ))
        }
    
    def predict_price(self, car_data: Dict[str, Any]) -> Dict[str, Any]:
        """Predict price for a single car."""
        if not self.is_trained:
            return {"error": "Model not trained"}
        
        # Prepare features
        features = []
        for col in self.feature_columns:
            value = car_data.get(col)
            
            if col in ['fuel_type', 'transmission', 'body_type', 'color', 'dealer_type']:
                # Handle categorical features
                if value is None:
                    value = 'unknown'
                value = str(value)
                if value not in self.label_encoders[col].classes_:
                    value = 'unknown'
                features.append(self.label_encoders[col].transform([value])[0])
            else:
                # Handle numerical features
                if value is None:
                    # Use median values from training
                    if col == 'year':
                        value = 2020
                    elif col == 'mileage':
                        value = 50000
                    elif col == 'engine_power':
                        value = 300
                    elif col == 'engine_displacement':
                        value = 3.0
                features.append(float(value))
        
        # Scale features
        X = np.array(features).reshape(1, -1)
        X_scaled = self.scaler.transform(X)
        
        # Predict
        predicted_price = self.model.predict(X_scaled)[0]
        
        # Calculate confidence based on feature completeness
        completeness = sum(1 for v in car_data.values() if v is not None) / len(car_data)
        confidence = min(0.9, completeness * 0.8)
        
        return {
            "predicted_price": float(predicted_price),
            "confidence": confidence,
            "features_used": self.feature_columns,
            "feature_values": dict(zip(self.feature_columns, features))
        }
    
    def analyze_market(self, car_ads: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze market trends and provide insights."""
        if not car_ads:
            return {"error": "No data available"}
        
        df = pd.DataFrame(car_ads)
        df = df.dropna(subset=['price'])
        
        if len(df) == 0:
            return {"error": "No price data available"}
        
        analysis = {
            "market_overview": self._analyze_market_overview(df),
            "price_trends": self._analyze_price_trends(df),
            "dealer_analysis": self._analyze_dealers(df),
            "condition_analysis": self._analyze_conditions(df),
            "recommendations": []
        }
        
        # Generate recommendations
        analysis["recommendations"] = self._generate_recommendations(analysis)
        
        return analysis
    
    def _analyze_market_overview(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Analyze overall market conditions."""
        return {
            "total_listings": len(df),
            "average_price": float(df['price'].mean()),
            "median_price": float(df['price'].median()),
            "price_range": {
                "min": float(df['price'].min()),
                "max": float(df['price'].max())
            },
            "price_std": float(df['price'].std())
        }
    
    def _analyze_price_trends(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Analyze price trends by various factors."""
        trends = {}
        
        # Price by year
        if 'year' in df.columns:
            year_prices = df.groupby('year')['price'].agg(['mean', 'count']).reset_index()
            trends['by_year'] = {
                row['year']: {'avg_price': float(row['mean']), 'count': int(row['count'])}
                for _, row in year_prices.iterrows()
            }
        
        # Price by mileage
        if 'mileage' in df.columns:
            df['mileage_bucket'] = pd.cut(df['mileage'], bins=5, labels=['Very Low', 'Low', 'Medium', 'High', 'Very High'])
            mileage_prices = df.groupby('mileage_bucket')['price'].mean()
            trends['by_mileage'] = {str(k): float(v) for k, v in mileage_prices.items()}
        
        return trends
    
    def _analyze_dealers(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Analyze dealer pricing patterns."""
        if 'dealer_type' not in df.columns:
            return {}
        
        dealer_analysis = df.groupby('dealer_type')['price'].agg(['mean', 'count', 'std']).reset_index()
        
        return {
            row['dealer_type']: {
                'avg_price': float(row['mean']),
                'listing_count': int(row['count']),
                'price_volatility': float(row['std']) if not pd.isna(row['std']) else 0.0
            }
            for _, row in dealer_analysis.iterrows()
        }
    
    def _analyze_conditions(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Analyze car conditions and their impact on price."""
        # This would integrate with image analysis results
        # For now, we'll use basic heuristics
        
        condition_analysis = {
            "high_mileage_impact": 0.0,
            "year_impact": 0.0,
            "condition_factors": []
        }
        
        if 'mileage' in df.columns and 'year' in df.columns:
            # Calculate depreciation impact
            df['age'] = 2024 - df['year']
            df['mileage_per_year'] = df['mileage'] / (df['age'] + 1)
            
            # High mileage impact
            high_mileage = df[df['mileage_per_year'] > 20000]
            if len(high_mileage) > 0:
                condition_analysis["high_mileage_impact"] = float(
                    (df['price'].mean() - high_mileage['price'].mean()) / df['price'].mean()
                )
                condition_analysis["condition_factors"].append("High mileage reduces value")
        
        return condition_analysis
    
    def _generate_recommendations(self, analysis: Dict[str, Any]) -> List[str]:
        """Generate market recommendations."""
        recommendations = []
        
        market = analysis.get("market_overview", {})
        trends = analysis.get("price_trends", {})
        
        # Price recommendations
        if market.get("price_std", 0) > market.get("average_price", 0) * 0.3:
            recommendations.append("High price volatility - good time for negotiations")
        
        # Year recommendations
        if "by_year" in trends:
            year_data = trends["by_year"]
            if len(year_data) > 1:
                years = sorted(year_data.keys())
                if years[-1] - years[0] > 2:
                    recommendations.append("Consider older models for better value")
        
        # Mileage recommendations
        if "by_mileage" in trends:
            mileage_data = trends["by_mileage"]
            if "Low" in mileage_data and "High" in mileage_data:
                low_price = mileage_data["Low"]
                high_price = mileage_data["High"]
                if low_price < high_price * 0.8:
                    recommendations.append("Low mileage cars offer good value")
        
        return recommendations
    
    def save_model(self):
        """Save the trained model and encoders."""
        if not self.is_trained:
            return
        
        # Create directory if it doesn't exist
        self.model_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Save model and metadata
        model_data = {
            'model': self.model,
            'label_encoders': self.label_encoders,
            'scaler': self.scaler,
            'feature_columns': self.feature_columns,
            'is_trained': self.is_trained
        }
        
        joblib.dump(model_data, self.model_path)
        logger.info(f"Model saved to {self.model_path}")
    
    def load_model(self):
        """Load existing model and encoders."""
        if not self.model_path.exists():
            return
        
        try:
            model_data = joblib.load(self.model_path)
            self.model = model_data['model']
            self.label_encoders = model_data['label_encoders']
            self.scaler = model_data['scaler']
            self.feature_columns = model_data['feature_columns']
            self.is_trained = model_data['is_trained']
            logger.info(f"Model loaded from {self.model_path}")
        except Exception as e:
            logger.error(f"Error loading model: {e}")
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the current model."""
        return {
            "is_trained": self.is_trained,
            "feature_columns": self.feature_columns,
            "model_type": "RandomForestRegressor",
            "model_path": str(self.model_path)
        }


# Example usage
if __name__ == "__main__":
    predictor = CarPricePredictor()
    
    # Example car data
    sample_cars = [
        {
            "year": 2020,
            "mileage": 50000,
            "engine_power": 600,
            "fuel_type": "Бензинов",
            "transmission": "Автоматична",
            "price": 80000
        },
        {
            "year": 2019,
            "mileage": 80000,
            "engine_power": 600,
            "fuel_type": "Бензинов", 
            "transmission": "Автоматична",
            "price": 70000
        }
    ]
    
    # Train model
    result = predictor.train_model(sample_cars)
    print("Training result:", result)
    
    # Predict price
    test_car = {
        "year": 2021,
        "mileage": 30000,
        "engine_power": 600,
        "fuel_type": "Бензинов",
        "transmission": "Автоматична"
    }
    
    prediction = predictor.predict_price(test_car)
    print("Price prediction:", prediction)
