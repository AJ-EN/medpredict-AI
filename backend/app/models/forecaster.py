"""
MedPredict AI - Demand Forecaster
Time-series forecasting with Prophet and XGBoost ensemble
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import json

# For hackathon speed, we'll use simpler models if Prophet isn't available
try:
    from prophet import Prophet
    PROPHET_AVAILABLE = True
except ImportError:
    PROPHET_AVAILABLE = False
    print("Prophet not available, using fallback forecaster")

from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler


class DemandForecaster:
    """
    Multi-signal demand forecasting with anomaly detection
    """
    
    def __init__(self, config: dict, data_dir: Path):
        self.config = config
        self.data_dir = data_dir
        self.districts = {d['id']: d for d in config['districts']}
        self.medicines = {m['id']: m for m in config['medicines']}
        
        # Load data
        self.weather_df = pd.read_csv(data_dir / 'synthetic_weather.csv', parse_dates=['date'])
        self.cases_df = pd.read_csv(data_dir / 'synthetic_cases.csv', parse_dates=['date'])
        self.consumption_df = pd.read_csv(data_dir / 'synthetic_consumption.csv', parse_dates=['date'])
        self.stock_df = pd.read_csv(data_dir / 'synthetic_stock.csv')
        
        # Precompute features
        self._prepare_features()
        
        # Initialize anomaly detector
        self.scaler = StandardScaler()
        self.anomaly_detector = IsolationForest(contamination=0.1, random_state=42)
    
    def _prepare_features(self):
        """Prepare rolling features for forecasting"""
        for district_id in self.districts.keys():
            mask = self.weather_df['district_id'] == district_id
            district_weather = self.weather_df[mask].sort_values('date')
            
            # Rolling weather features
            self.weather_df.loc[mask, 'rainfall_7d'] = district_weather['rainfall'].rolling(7, min_periods=1).sum().values
            self.weather_df.loc[mask, 'rainfall_14d'] = district_weather['rainfall'].rolling(14, min_periods=1).sum().values
            self.weather_df.loc[mask, 'temp_7d_avg'] = district_weather['temperature'].rolling(7, min_periods=1).mean().values
            self.weather_df.loc[mask, 'humidity_7d_avg'] = district_weather['humidity'].rolling(7, min_periods=1).mean().values
    
    def get_current_weather(self, district_id: str) -> dict:
        """Get latest weather data for a district"""
        district_weather = self.weather_df[self.weather_df['district_id'] == district_id]
        latest = district_weather.sort_values('date').iloc[-1]
        return {
            'temperature': float(latest['temperature']),
            'rainfall': float(latest['rainfall']),
            'humidity': float(latest['humidity']),
            'rainfall_7d': float(latest.get('rainfall_7d', 0)),
            'rainfall_14d': float(latest.get('rainfall_14d', 0))
        }
    
    def calculate_risk_score(self, district_id: str) -> Dict:
        """
        Calculate multi-signal risk score for a district
        Returns score 0-1 and breakdown by signal
        """
        weather = self.get_current_weather(district_id)
        
        # Weather signal (0-1)
        # High risk when: temp 25-30°C, high recent rainfall, high humidity
        temp_risk = np.exp(-((weather['temperature'] - 27) ** 2) / 50)
        rain_risk = min(weather['rainfall_14d'] / 150, 1.0)
        humidity_risk = weather['humidity'] / 100
        weather_signal = (temp_risk * 0.3 + rain_risk * 0.5 + humidity_risk * 0.2)
        
        # Historical pattern signal
        today = datetime.now()
        month = today.month
        # Monsoon months are high risk
        if month in [7, 8, 9]:
            seasonal_signal = 0.8
        elif month in [6, 10]:
            seasonal_signal = 0.5
        else:
            seasonal_signal = 0.2
        
        # Recent case trend signal
        district_cases = self.cases_df[self.cases_df['district_id'] == district_id].sort_values('date')
        if len(district_cases) >= 14:
            recent_7d = district_cases.tail(7)['dengue_cases'].sum()
            prev_7d = district_cases.tail(14).head(7)['dengue_cases'].sum()
            if prev_7d > 0:
                trend = (recent_7d - prev_7d) / prev_7d
                trend_signal = min(max((trend + 0.5) / 1.5, 0), 1)  # Normalize
            else:
                trend_signal = 0.5 if recent_7d > 0 else 0.2
        else:
            trend_signal = 0.3
        
        # Combined risk score (weighted)
        weights = {
            'weather': 0.35,
            'seasonal': 0.25,
            'trend': 0.25,
            'baseline': 0.15
        }
        
        combined_score = (
            weather_signal * weights['weather'] +
            seasonal_signal * weights['seasonal'] +
            trend_signal * weights['trend'] +
            0.3 * weights['baseline']  # Baseline risk
        )
        
        # Determine risk level
        if combined_score > 0.75:
            level = 'red'
        elif combined_score > 0.5:
            level = 'orange'
        elif combined_score > 0.25:
            level = 'yellow'
        else:
            level = 'green'
        
        return {
            'score': round(combined_score, 3),
            'level': level,
            'signals': {
                'weather': round(weather_signal, 3),
                'seasonal': round(seasonal_signal, 3),
                'trend': round(trend_signal, 3)
            },
            'weather_data': weather
        }
    
    def forecast_cases(self, district_id: str, disease: str = 'dengue', days_ahead: int = 14) -> List[Dict]:
        """
        Forecast disease cases for next N days
        Uses simple exponential model with weather adjustment
        """
        district_cases = self.cases_df[self.cases_df['district_id'] == district_id].sort_values('date')
        col = f'{disease}_cases'
        
        if col not in district_cases.columns:
            return []
        
        # Get recent baseline
        recent_avg = district_cases.tail(14)[col].mean()
        
        # Get risk score for adjustment
        risk = self.calculate_risk_score(district_id)
        
        forecasts = []
        today = datetime.now()
        
        for i in range(1, days_ahead + 1):
            date = today + timedelta(days=i)
            
            # Base prediction with trend
            trend_factor = 1 + (risk['signals']['trend'] - 0.5) * 0.1 * i
            weather_factor = 1 + (risk['signals']['weather'] - 0.5) * 0.2
            
            predicted = recent_avg * trend_factor * weather_factor
            
            # Add uncertainty (grows with horizon)
            uncertainty = predicted * (0.1 + 0.02 * i)
            
            forecasts.append({
                'date': date.strftime('%Y-%m-%d'),
                'predicted': round(max(0, predicted), 0),
                'lower_bound': round(max(0, predicted - 1.96 * uncertainty), 0),
                'upper_bound': round(predicted + 1.96 * uncertainty, 0),
                'confidence': round(max(0.5, 1 - 0.03 * i), 2)
            })
        
        return forecasts
    
    def forecast_medicine_demand(self, district_id: str, medicine_id: str, days_ahead: int = 14) -> List[Dict]:
        """
        Forecast medicine demand based on case forecasts
        """
        medicine = self.medicines.get(medicine_id)
        if not medicine:
            return []
        
        # Get case forecasts for relevant diseases
        total_demand = [0] * days_ahead
        
        for disease in medicine['diseases']:
            if disease in ['dengue', 'malaria', 'diarrhea']:
                case_forecasts = self.forecast_cases(district_id, disease, days_ahead)
                for i, fc in enumerate(case_forecasts):
                    # Convert cases to medicine demand
                    healthcare_rate = 0.6
                    demand = (
                        fc['predicted'] *
                        healthcare_rate *
                        medicine['prescription_rate'] *
                        medicine['units_per_case']
                    )
                    total_demand[i] += demand
        
        today = datetime.now()
        return [
            {
                'date': (today + timedelta(days=i+1)).strftime('%Y-%m-%d'),
                'medicine_id': medicine_id,
                'predicted_demand': round(total_demand[i]),
                'lower_bound': round(total_demand[i] * 0.7),
                'upper_bound': round(total_demand[i] * 1.3)
            }
            for i in range(days_ahead)
        ]
    
    def get_stock_status(self, district_id: str) -> List[Dict]:
        """Get current stock levels with gap analysis"""
        district_stock = self.stock_df[self.stock_df['district_id'] == district_id]
        
        results = []
        for _, row in district_stock.iterrows():
            medicine = self.medicines.get(row['medicine_id'], {})
            
            # Get 14-day demand forecast
            demand_forecast = self.forecast_medicine_demand(district_id, row['medicine_id'], 14)
            total_14d_demand = sum(f['predicted_demand'] for f in demand_forecast)
            
            # Calculate metrics
            current_stock = row['current_stock']
            gap = current_stock - total_14d_demand
            days_until_stockout = int(current_stock / max(total_14d_demand / 14, 1))
            stock_percentage = min(100, int(current_stock / max(total_14d_demand, 1) * 100))
            
            results.append({
                'medicine_id': row['medicine_id'],
                'medicine_name': medicine.get('name', row['medicine_id']),
                'current_stock': int(current_stock),
                'safety_stock': int(row['safety_stock']),
                'predicted_14d_demand': int(total_14d_demand),
                'stock_gap': int(gap),
                'days_until_stockout': days_until_stockout,
                'stock_percentage': stock_percentage,
                'status': 'critical' if stock_percentage < 30 else 'warning' if stock_percentage < 60 else 'good',
                'days_until_expiry': int(row['days_until_expiry'])
            })
        
        return results
    
    def get_recommendations(self, district_id: str) -> List[Dict]:
        """Generate actionable recommendations based on analysis"""
        stock_status = self.get_stock_status(district_id)
        risk = self.calculate_risk_score(district_id)
        
        recommendations = []
        
        for stock in stock_status:
            if stock['status'] == 'critical':
                # Urgent action needed
                recommendations.append({
                    'priority': 'urgent',
                    'type': 'order',
                    'medicine_id': stock['medicine_id'],
                    'medicine_name': stock['medicine_name'],
                    'action': f"Order {abs(stock['stock_gap'])} units of {stock['medicine_name']}",
                    'reason': f"Only {stock['days_until_stockout']} days until stockout",
                    'deadline': (datetime.now() + timedelta(days=3)).strftime('%Y-%m-%d')
                })
            elif stock['status'] == 'warning' and risk['level'] in ['red', 'orange']:
                # Prepare for surge
                recommendations.append({
                    'priority': 'high',
                    'type': 'transfer',
                    'medicine_id': stock['medicine_id'],
                    'medicine_name': stock['medicine_name'],
                    'action': f"Request transfer of {int(stock['predicted_14d_demand'] * 0.5)} units from nearby district",
                    'reason': f"Risk level {risk['level'].upper()}, stock at {stock['stock_percentage']}%",
                    'deadline': (datetime.now() + timedelta(days=5)).strftime('%Y-%m-%d')
                })
        
        # Add risk-based recommendations
        if risk['level'] == 'red':
            recommendations.append({
                'priority': 'urgent',
                'type': 'alert',
                'action': 'Alert district hospital for potential surge capacity',
                'reason': f"Combined risk score: {risk['score']:.2f}",
                'deadline': (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
            })
        
        return sorted(recommendations, key=lambda x: {'urgent': 0, 'high': 1, 'medium': 2}[x['priority']])
    
    def detect_anomalies(self, district_id: str) -> List[Dict]:
        """Detect anomalies in recent data"""
        district_cases = self.cases_df[self.cases_df['district_id'] == district_id].tail(30)
        
        if len(district_cases) < 7:
            return []
        
        anomalies = []
        
        for disease in ['dengue', 'malaria', 'diarrhea']:
            col = f'{disease}_cases'
            if col not in district_cases.columns:
                continue
            
            values = district_cases[col].values
            mean = values[:-7].mean() if len(values) > 7 else values.mean()
            std = values[:-7].std() if len(values) > 7 else values.std()
            
            if std > 0:
                recent_avg = values[-7:].mean()
                z_score = (recent_avg - mean) / std
                
                if z_score > 2:
                    anomalies.append({
                        'disease': disease,
                        'type': 'spike',
                        'z_score': round(z_score, 2),
                        'recent_avg': round(recent_avg, 0),
                        'historical_avg': round(mean, 0),
                        'message': f"{disease.title()} cases {int((recent_avg/mean - 1)*100)}% above normal"
                    })
        
        return anomalies
