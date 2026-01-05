"""
MedPredict AI - Causal Demand Forecaster (UPGRADED)
Implements proper biological lag modeling and safety stock calculations

Key Upgrades:
1. CAUSAL LAG: Uses rainfall from 14-21 days ago to predict cases today
2. SAFETY STOCK: Adds uncertainty-based buffer, not just gap filling
3. NETWORK AWARE: Considers inter-district transfers before ordering
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import json

from sklearn.ensemble import IsolationForest, GradientBoostingRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split


class CausalDemandForecaster:
    """
    FIRST PRINCIPLES FORECASTER
    
    Key insight: Biological systems have lag.
    - Rain on Day 0 → Mosquitoes on Day 7 → Cases on Day 14-21
    
    We don't predict "if rain today, cases today"
    We predict "given rain 2 weeks ago, what cases tomorrow?"
    """
    
    # Biological lag constants (days)
    DENGUE_LAG = 14  # Rain → Cases takes ~14 days
    MALARIA_LAG = 21  # Longer incubation
    DIARRHEA_LAG = 3  # Shorter (water contamination)
    
    # Service level for safety stock (97.5% = 1.96 z-score)
    SERVICE_LEVEL_Z = 1.96
    
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
        
        # Prepare causal features
        self._prepare_causal_features()
        
        # Train models
        self.models = {}
        self._train_causal_models()
    
    def _prepare_causal_features(self):
        """
        CRITICAL: Create LAGGED features that respect biological causality
        
        We shift weather data BACKWARDS so that:
        - weather_lagged_14d on Day 30 = actual weather on Day 16
        - This means: "weather from 14 days ago predicts today's cases"
        """
        for district_id in self.districts.keys():
            # Get district weather
            mask = self.weather_df['district_id'] == district_id
            district_weather = self.weather_df[mask].sort_values('date').copy()
            
            # Create lagged features for dengue (14-day lag)
            district_weather['rainfall_lag_14d'] = district_weather['rainfall'].shift(self.DENGUE_LAG)
            district_weather['rainfall_sum_lag_14d'] = district_weather['rainfall'].rolling(7).sum().shift(self.DENGUE_LAG)
            district_weather['temp_lag_14d'] = district_weather['temperature'].shift(self.DENGUE_LAG)
            district_weather['humidity_lag_14d'] = district_weather['humidity'].shift(self.DENGUE_LAG)
            
            # Mosquito Breeding Index: optimal at 25-28°C with rain
            district_weather['breeding_index_lag'] = (
                np.exp(-((district_weather['temp_lag_14d'] - 27) ** 2) / 50) * 
                np.clip(district_weather['rainfall_sum_lag_14d'] / 50, 0, 2)
            )
            
            # Update back to main dataframe
            self.weather_df.loc[mask, 'rainfall_lag_14d'] = district_weather['rainfall_lag_14d'].values
            self.weather_df.loc[mask, 'rainfall_sum_lag_14d'] = district_weather['rainfall_sum_lag_14d'].values
            self.weather_df.loc[mask, 'temp_lag_14d'] = district_weather['temp_lag_14d'].values
            self.weather_df.loc[mask, 'humidity_lag_14d'] = district_weather['humidity_lag_14d'].values
            self.weather_df.loc[mask, 'breeding_index_lag'] = district_weather['breeding_index_lag'].values
    
    def _train_causal_models(self):
        """
        Train a causal model for each district
        Uses Gradient Boosting with lagged features as predictors
        """
        for district_id in self.districts.keys():
            # Merge weather (with lags) and cases
            weather = self.weather_df[self.weather_df['district_id'] == district_id].copy()
            cases = self.cases_df[self.cases_df['district_id'] == district_id].copy()
            
            df = pd.merge(weather, cases, on=['date', 'district_id'], how='inner')
            df = df.dropna()
            
            if len(df) < 30:
                continue
            
            # Features: LAGGED weather (the cause)
            # Target: Cases today (the effect)
            feature_cols = [
                'rainfall_lag_14d',
                'rainfall_sum_lag_14d',
                'temp_lag_14d',
                'humidity_lag_14d',
                'breeding_index_lag'
            ]
            
            X = df[feature_cols].fillna(0)
            y = df['dengue_cases']
            
            # Train Gradient Boosting Regressor
            model = GradientBoostingRegressor(
                n_estimators=50,
                max_depth=4,
                learning_rate=0.1,
                random_state=42
            )
            model.fit(X, y)
            
            self.models[district_id] = {
                'model': model,
                'feature_cols': feature_cols,
                'y_std': y.std(),  # For uncertainty estimation
                'y_mean': y.mean()
            }
    
    def get_current_weather(self, district_id: str) -> dict:
        """Get latest weather data including lagged features"""
        district_weather = self.weather_df[self.weather_df['district_id'] == district_id]
        latest = district_weather.sort_values('date').iloc[-1]
        return {
            'temperature': float(latest['temperature']),
            'rainfall': float(latest['rainfall']),
            'humidity': float(latest['humidity']),
            'rainfall_lag_14d': float(latest.get('rainfall_lag_14d', 0)),
            'breeding_index_lag': float(latest.get('breeding_index_lag', 0)),
            # Note: These are the CAUSAL features - weather from 2 weeks ago
        }
    
    def calculate_risk_score(self, district_id: str) -> Dict:
        """
        CAUSAL Risk Score: Based on PAST weather, not current conditions
        
        Key insight: If it rained heavily 14 days ago, risk is HIGH now
        even if today is sunny.
        """
        weather = self.get_current_weather(district_id)
        
        # Causal weather signal (from 14 days ago)
        breeding_index = weather.get('breeding_index_lag', 0)
        causal_weather_signal = min(breeding_index / 1.5, 1.0) if breeding_index else 0.3
        
        # Seasonal signal
        today = datetime.now()
        month = today.month
        if month in [7, 8, 9]:  # Monsoon
            seasonal_signal = 0.8
        elif month in [6, 10]:
            seasonal_signal = 0.5
        else:
            seasonal_signal = 0.2
        
        # Trend signal from recent cases
        district_cases = self.cases_df[self.cases_df['district_id'] == district_id].sort_values('date')
        if len(district_cases) >= 14:
            recent_7d = district_cases.tail(7)['dengue_cases'].sum()
            prev_7d = district_cases.tail(14).head(7)['dengue_cases'].sum()
            if prev_7d > 0:
                trend = (recent_7d - prev_7d) / prev_7d
                trend_signal = min(max((trend + 0.5) / 1.5, 0), 1)
            else:
                trend_signal = 0.5 if recent_7d > 0 else 0.2
        else:
            trend_signal = 0.3
        
        # Combined (CAUSAL weather weighted more heavily)
        weights = {
            'causal_weather': 0.45,  # This is the causal predictor
            'seasonal': 0.25,
            'trend': 0.20,
            'baseline': 0.10
        }
        
        combined_score = (
            causal_weather_signal * weights['causal_weather'] +
            seasonal_signal * weights['seasonal'] +
            trend_signal * weights['trend'] +
            0.3 * weights['baseline']
        )
        
        # Risk level
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
                'causal_weather': round(causal_weather_signal, 3),
                'seasonal': round(seasonal_signal, 3),
                'trend': round(trend_signal, 3)
            },
            'weather_data': weather,
            'causal_note': "Risk based on weather from 14 days ago (biological lag)"
        }
    
    def forecast_cases(self, district_id: str, disease: str = 'dengue', days_ahead: int = 14) -> List[Dict]:
        """
        CAUSAL Forecast: Uses lagged weather features
        
        To predict Day T, we use weather from Day T-14.
        Since we KNOW weather from the past, we can predict the future.
        """
        if district_id not in self.models:
            # Fallback to simple average
            return self._simple_forecast(district_id, disease, days_ahead)
        
        model_info = self.models[district_id]
        model = model_info['model']
        feature_cols = model_info['feature_cols']
        y_std = model_info['y_std']
        
        weather = self.weather_df[self.weather_df['district_id'] == district_id].sort_values('date')
        
        forecasts = []
        today = datetime.now()
        
        for i in range(1, days_ahead + 1):
            forecast_date = today + timedelta(days=i)
            
            # To predict Day T+i, we need weather from Day (T+i - 14) = Day (T+i-14)
            # If i <= 14, we have this data (it's in the past)
            # If i > 14, we'd need weather forecast (not available in demo)
            
            if i <= 14:
                # We have the causal data!
                lookback_idx = -14 + i
                if abs(lookback_idx) <= len(weather):
                    row = weather.iloc[lookback_idx]
                    features = pd.DataFrame([[
                        row.get('rainfall_lag_14d', 0),
                        row.get('rainfall_sum_lag_14d', 0),
                        row.get('temp_lag_14d', 0),
                        row.get('humidity_lag_14d', 0),
                        row.get('breeding_index_lag', 0)
                    ]], columns=feature_cols).fillna(0)
                    
                    predicted = max(0, model.predict(features)[0])
                else:
                    predicted = model_info['y_mean']
            else:
                # Beyond causal horizon - use mean with higher uncertainty
                predicted = model_info['y_mean']
            
            # Uncertainty grows with forecast horizon
            uncertainty_factor = 1 + 0.05 * i  # 5% per day
            uncertainty = y_std * uncertainty_factor
            
            forecasts.append({
                'date': forecast_date.strftime('%Y-%m-%d'),
                'predicted': round(max(0, predicted), 0),
                'lower_bound': round(max(0, predicted - 1.96 * uncertainty), 0),
                'upper_bound': round(predicted + 1.96 * uncertainty, 0),
                'confidence': round(max(0.3, 1 - 0.04 * i), 2),
                'is_causal': i <= 14  # True if based on actual lagged data
            })
        
        return forecasts
    
    def _simple_forecast(self, district_id: str, disease: str, days_ahead: int) -> List[Dict]:
        """Fallback: simple average-based forecast"""
        district_cases = self.cases_df[self.cases_df['district_id'] == district_id]
        col = f'{disease}_cases'
        if col not in district_cases.columns:
            avg = 10
        else:
            avg = district_cases[col].mean()
        
        today = datetime.now()
        return [
            {
                'date': (today + timedelta(days=i)).strftime('%Y-%m-%d'),
                'predicted': round(avg),
                'lower_bound': round(avg * 0.5),
                'upper_bound': round(avg * 1.5),
                'confidence': 0.5,
                'is_causal': False
            }
            for i in range(1, days_ahead + 1)
        ]
    
    def forecast_medicine_demand(self, district_id: str, medicine_id: str, days_ahead: int = 14) -> List[Dict]:
        """Convert case forecasts to medicine demand"""
        medicine = self.medicines.get(medicine_id)
        if not medicine:
            return []
        
        total_demand = [0.0] * days_ahead
        uncertainty = [0.0] * days_ahead
        
        for disease in medicine['diseases']:
            if disease in ['dengue', 'malaria', 'diarrhea']:
                case_forecasts = self.forecast_cases(district_id, disease, days_ahead)
                for i, fc in enumerate(case_forecasts):
                    healthcare_rate = 0.6
                    demand = (
                        fc['predicted'] *
                        healthcare_rate *
                        medicine['prescription_rate'] *
                        medicine['units_per_case']
                    )
                    total_demand[i] += demand
                    
                    # Track uncertainty
                    uncertainty[i] += (fc['upper_bound'] - fc['predicted']) * healthcare_rate * medicine['prescription_rate'] * medicine['units_per_case']
        
        today = datetime.now()
        return [
            {
                'date': (today + timedelta(days=i+1)).strftime('%Y-%m-%d'),
                'medicine_id': medicine_id,
                'predicted_demand': round(total_demand[i]),
                'lower_bound': round(total_demand[i] * 0.7),
                'upper_bound': round(total_demand[i] + uncertainty[i]),
                'uncertainty': round(uncertainty[i])
            }
            for i in range(days_ahead)
        ]
    
    def calculate_safety_stock(self, district_id: str, medicine_id: str, lead_time_days: int = 7) -> int:
        """
        FIRST PRINCIPLES Safety Stock Calculation
        
        Formula: Safety Stock = Z × σ × √(Lead Time)
        
        Where:
        - Z = Service level factor (1.96 for 97.5%)
        - σ = Standard deviation of daily demand
        - Lead Time = Days from order to delivery
        """
        # Get historical demand variance
        consumption = self.consumption_df[
            (self.consumption_df['district_id'] == district_id) &
            (self.consumption_df['medicine_id'] == medicine_id)
        ]['consumption']
        
        if len(consumption) < 7:
            return 100  # Minimum safety stock
        
        daily_std = consumption.std()
        
        # Safety Stock Formula
        safety_stock = self.SERVICE_LEVEL_Z * daily_std * np.sqrt(lead_time_days)
        
        return int(max(safety_stock, 50))  # Minimum 50 units
    
    def get_stock_status(self, district_id: str) -> List[Dict]:
        """Get stock with safety stock calculations"""
        district_stock = self.stock_df[self.stock_df['district_id'] == district_id]
        
        results = []
        for _, row in district_stock.iterrows():
            medicine = self.medicines.get(row['medicine_id'], {})
            
            # Get 14-day demand forecast
            demand_forecast = self.forecast_medicine_demand(district_id, row['medicine_id'], 14)
            total_14d_demand = sum(f['predicted_demand'] for f in demand_forecast)
            total_uncertainty = sum(f['uncertainty'] for f in demand_forecast)
            
            # Calculate proper safety stock
            safety_stock = self.calculate_safety_stock(district_id, row['medicine_id'])
            
            current_stock = row['current_stock']
            
            # Order point = Predicted demand + Safety stock
            order_point = total_14d_demand + safety_stock
            
            # Gap includes safety stock buffer
            gap = current_stock - order_point
            
            days_until_stockout = int(current_stock / max(total_14d_demand / 14, 1))
            stock_percentage = min(100, int(current_stock / max(order_point, 1) * 100))
            
            if stock_percentage < 30:
                status = 'critical'
            elif stock_percentage < 60:
                status = 'warning'
            else:
                status = 'good'
            
            results.append({
                'medicine_id': row['medicine_id'],
                'medicine_name': medicine.get('name', row['medicine_id']),
                'current_stock': int(current_stock),
                'safety_stock': safety_stock,
                'predicted_14d_demand': int(total_14d_demand),
                'demand_uncertainty': int(total_uncertainty),
                'order_point': int(order_point),
                'stock_gap': int(gap),
                'days_until_stockout': days_until_stockout,
                'stock_percentage': stock_percentage,
                'status': status,
                'days_until_expiry': int(row['days_until_expiry'])
            })
        
        return results
    
    def optimize_network_transfers(self) -> List[Dict]:
        """
        NETWORK OPTIMIZATION: Consider transfers before orders
        
        Simple greedy algorithm for hackathon:
        1. Find all surpluses and deficits
        2. Match surplus districts to deficit districts
        3. Only order if transfers can't fill the gap
        """
        transfers = []
        orders = []
        
        for med_id in self.medicines.keys():
            surpluses = []
            deficits = []
            
            for district_id in self.districts.keys():
                stock_status = self.get_stock_status(district_id)
                med_status = next((s for s in stock_status if s['medicine_id'] == med_id), None)
                
                if not med_status:
                    continue
                
                gap = med_status['stock_gap']
                
                if gap > 0:
                    # Surplus: can transfer out
                    surpluses.append({
                        'district_id': district_id,
                        'district_name': self.districts[district_id]['name'],
                        'surplus': gap
                    })
                elif gap < 0:
                    # Deficit: needs stock
                    deficits.append({
                        'district_id': district_id,
                        'district_name': self.districts[district_id]['name'],
                        'deficit': abs(gap)
                    })
            
            # Sort by amount
            surpluses.sort(key=lambda x: -x['surplus'])
            deficits.sort(key=lambda x: -x['deficit'])
            
            # Match surpluses to deficits
            for deficit in deficits:
                remaining_deficit = deficit['deficit']
                
                for surplus in surpluses:
                    if remaining_deficit <= 0:
                        break
                    if surplus['surplus'] <= 0:
                        continue
                    
                    transfer_qty = min(remaining_deficit, surplus['surplus'])
                    
                    transfers.append({
                        'medicine_id': med_id,
                        'medicine_name': self.medicines[med_id]['name'],
                        'from_district': surplus['district_name'],
                        'from_district_id': surplus['district_id'],
                        'to_district': deficit['district_name'],
                        'to_district_id': deficit['district_id'],
                        'quantity': int(transfer_qty),
                        'action': 'TRANSFER',
                        'priority': 'high',
                        'cost_saved': int(transfer_qty * 10)  # Transfer vs procurement
                    })
                    
                    surplus['surplus'] -= transfer_qty
                    remaining_deficit -= transfer_qty
                
                # If still deficit after transfers, order new stock
                if remaining_deficit > 0:
                    orders.append({
                        'medicine_id': med_id,
                        'medicine_name': self.medicines[med_id]['name'],
                        'district': deficit['district_name'],
                        'district_id': deficit['district_id'],
                        'quantity': int(remaining_deficit),
                        'action': 'ORDER',
                        'priority': 'urgent'
                    })
        
        return {'transfers': transfers, 'orders': orders}
    
    def get_recommendations(self, district_id: str) -> List[Dict]:
        """Generate recommendations using network-aware logic"""
        stock_status = self.get_stock_status(district_id)
        risk = self.calculate_risk_score(district_id)
        network_plan = self.optimize_network_transfers()
        
        recommendations = []
        
        # Get transfers/orders relevant to this district
        for transfer in network_plan['transfers']:
            if transfer['to_district_id'] == district_id:
                recommendations.append({
                    'priority': 'high',
                    'type': 'transfer_in',
                    'medicine_id': transfer['medicine_id'],
                    'medicine_name': transfer['medicine_name'],
                    'action': f"Request transfer of {transfer['quantity']} units from {transfer['from_district']}",
                    'reason': f"Network optimization: Uses existing surplus, saves ₹{transfer['cost_saved']}",
                    'deadline': (datetime.now() + timedelta(days=3)).strftime('%Y-%m-%d')
                })
        
        for order in network_plan['orders']:
            if order['district_id'] == district_id:
                recommendations.append({
                    'priority': 'urgent',
                    'type': 'order',
                    'medicine_id': order['medicine_id'],
                    'medicine_name': order['medicine_name'],
                    'action': f"Procure {order['quantity']} units of {order['medicine_name']}",
                    'reason': f"Deficit cannot be covered by inter-district transfer",
                    'deadline': (datetime.now() + timedelta(days=5)).strftime('%Y-%m-%d')
                })
        
        # Add risk-based alerts
        if risk['level'] == 'red':
            recommendations.append({
                'priority': 'urgent',
                'type': 'alert',
                'action': 'Alert district hospital for potential surge capacity',
                'reason': f"Causal risk score: {risk['score']:.2f} (based on weather 14 days ago)",
                'deadline': (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
            })
        
        return sorted(recommendations, key=lambda x: {'urgent': 0, 'high': 1, 'medium': 2}.get(x['priority'], 3))
    
    def detect_anomalies(self, district_id: str) -> List[Dict]:
        """Detect anomalies with causal context"""
        district_cases = self.cases_df[self.cases_df['district_id'] == district_id].tail(30)
        
        if len(district_cases) < 7:
            return []
        
        anomalies = []
        
        for disease in ['dengue', 'malaria', 'diarrhea']:
            col = f'{disease}_cases'
            if col not in district_cases.columns:
                continue
            
            values = district_cases[col].values
            if len(values) < 10:
                continue
                
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
                        'message': f"{disease.title()} cases {int((recent_avg/mean - 1)*100)}% above normal",
                        'causal_note': 'Check weather conditions 14 days ago for root cause'
                    })
        
        return anomalies


# Alias for backward compatibility
DemandForecaster = CausalDemandForecaster
