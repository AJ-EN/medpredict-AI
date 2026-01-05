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
from prophet import Prophet
import logging

# Suppress Prophet logs
logging.getLogger('prophet').setLevel(logging.ERROR)
logging.getLogger('cmdstanpy').setLevel(logging.ERROR)


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
        # Load data from DATABASE (Production Grade)
        from app.db.database import engine
        
        # We load full tables into memory for the ML model (Pandas optimizations)
        # In a massive scale system, we'd move this to on-demand queries, 
        # but for <1M rows, in-memory DataFrame is faster (Vectorized operations).
        
        self.weather_df = pd.read_sql("SELECT * FROM weatherlog", engine, parse_dates=['date'])
        raw_cases = pd.read_sql("SELECT * FROM diseasecase", engine, parse_dates=['date'])
        
        # Pivot to wide format (date, district_id as index, disease as columns)
        if not raw_cases.empty:
            self.cases_df = raw_cases.pivot_table(
                index=['date', 'district_id'], 
                columns='disease', 
                values='count', 
                fill_value=0
            ).reset_index()
            # Rename columns: dengue -> dengue_cases
            self.cases_df.columns = [
                f"{c}_cases" if c in ['dengue', 'malaria', 'diarrhea', 'flu'] else c 
                for c in self.cases_df.columns
            ]
        else:
             self.cases_df = pd.DataFrame(columns=['date', 'district_id', 'dengue_cases']) # Fallback
        
        # Consumption is derived or we need a table. 
        # For now, if we didn't migrate consumption, we can fallback or derive.
        # Check if we have consumption column or table. Models didn't have Consumption table.
        # We'll stick to CSV for consumption OR derive it. 
        # Implementation Plan didn't mention Consumption table. 
        # Let's keep consumption as CSV for now to avoid breaking or mock it.
        try:
             self.consumption_df = pd.read_csv(data_dir / 'synthetic_consumption.csv', parse_dates=['date'])
        except:
             self.consumption_df = pd.DataFrame() # Fallback
             
        self.stock_df = pd.read_sql("SELECT * FROM stock", engine)
        
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
        Train PROPHET model with Causal Regressors (Rainfall, Breeding Index)
        """
        print("Training Prophet Causal Models...")
        
        # Merge weather (with lags) and cases once for all districts
        self.merged_df = pd.merge(self.weather_df, self.cases_df, on=['date', 'district_id'], how='inner')
        self.merged_df = self.merged_df.dropna(subset=['dengue_cases', 'rainfall_lag_14d', 'breeding_index_lag'])
        
        for district_id in self.districts:
            # Prepare Training Data
            model_df = self.merged_df[self.merged_df['district_id'] == district_id].copy()
            
            if len(model_df) < 30:
                continue
                
            # Prepare Prophet DataFrame
            prophet_df = model_df[['date', 'dengue_cases', 'rainfall_lag_14d', 'breeding_index_lag']].copy()
            prophet_df.columns = ['ds', 'y', 'rainfall_lag_14d', 'breeding_index_lag']
            
            try:
                # Initialize Prophet with seasonality
                m = Prophet(yearly_seasonality=True, weekly_seasonality=True, daily_seasonality=False)
                
                # Add Causal Regressors
                m.add_regressor('rainfall_lag_14d')
                m.add_regressor('breeding_index_lag')
                
                # Fit Model
                m.fit(prophet_df)
                
                # Store Model
                self.models[district_id] = {
                    'type': 'prophet',
                    'model': m,
                    'last_date': model_df['date'].max()
                }
            except Exception as e:
                print(f"Failed to train Prophet for {district_id}: {e}")
    
    async def get_current_weather(self, district_id: str) -> dict:
        """
        Get latest weather data.
        HYBRID: Tries to get REAL data from OpenWeatherMap API first.
        Falls back to synthetic CSV data if API fails.
        """
        # Try to get real data
        from app.services.weather_service import weather_service
        
        real_data = None
        district = self.districts.get(district_id)
        
        if district and 'lat' in district and 'lng' in district:
            real_data = await weather_service.get_current_weather(
                district['lat'], 
                district['lng'], 
                district_id
            )
            
        # Get synthetic data (for historical context/lag)
        district_weather = self.weather_df[self.weather_df['district_id'] == district_id]
        latest_synthetic = district_weather.sort_values('date').iloc[-1]
        
        if real_data:
            # We have real data!
            # SAVE TO DB (Data Engineering Pipeline)
            try:
                from sqlmodel import Session
                from app.db.database import engine
                from app.db.models import WeatherLog
                
                with Session(engine) as session:
                    # Check if log exists for today to avoid duplicates
                    today = datetime.now().date()
                    existing = session.query(WeatherLog).filter(
                        WeatherLog.district_id == district_id,
                        WeatherLog.date == today
                    ).first()
                    
                    if not existing:
                        log = WeatherLog(
                            district_id=district_id,
                            date=today,
                            temperature=real_data['temperature'],
                            rainfall=real_data['rainfall'],
                            humidity=real_data['humidity'],
                            is_forecast=False,
                            source="openweathermap"
                        )
                        session.add(log)
                        session.commit()
            except Exception as e:
                print(f"Error saving weather log: {e}")

            # Note: For 'rainfall_lag_14d', we still need history.
            # In a full production system, we would query our DB for 14-day old real data.
            # For now, we mix Real Current w/ Synthetic Past.
            return {
                'temperature': float(real_data['temperature']),
                'rainfall': float(real_data['rainfall']),
                'humidity': float(real_data['humidity']),
                'condition': real_data.get('condition', 'Unknown'),
                'is_real_data': True,
                # Lagged features still come from CSV for now
                'rainfall_lag_14d': float(latest_synthetic.get('rainfall_lag_14d', 0)),
                'breeding_index_lag': float(latest_synthetic.get('breeding_index_lag', 0)),
            }
        else:
            # Fallback to pure synthetic
            return {
                'temperature': float(latest_synthetic['temperature']),
                'rainfall': float(latest_synthetic['rainfall']),
                'humidity': float(latest_synthetic['humidity']),
                'condition': 'Simulated',
                'is_real_data': False,
                'rainfall_lag_14d': float(latest_synthetic.get('rainfall_lag_14d', 0)),
                'breeding_index_lag': float(latest_synthetic.get('breeding_index_lag', 0)),
            }
    
    async def calculate_risk_score(self, district_id: str) -> Dict:
        """
        CAUSAL Risk Score: Based on PAST weather + REAL TIME Signal
        """
        weather = await self.get_current_weather(district_id)
        
        # 1. Causal Signal (Past -> Present Risk)
        breeding_index = weather.get('breeding_index_lag', 0)
        causal_weather_signal = min(breeding_index / 1.5, 1.0) if breeding_index else 0.3
        
        # 2. Real-Time Signal (Present -> Future Risk)
        # If it is raining NOW, we flag a future risk
        real_time_signal = 0.0
        if weather.get('is_real_data'):
            if weather['rainfall'] > 5.0 and weather['temperature'] > 20:
                 real_time_signal = 0.8  # High risk forming
            elif weather['rainfall'] > 0:
                 real_time_signal = 0.4
        
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
        
        # Combined (Weighted)
        weights = {
            'causal_weather': 0.40,
            'seasonal': 0.20,
            'trend': 0.20,
            'real_time': 0.10, # Bonus from real data
            'baseline': 0.10
        }
        
        combined_score = (
            causal_weather_signal * weights['causal_weather'] +
            seasonal_signal * weights['seasonal'] +
            trend_signal * weights['trend'] +
            real_time_signal * weights['real_time'] +
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
                'trend': round(trend_signal, 3),
                'real_time_warning': round(real_time_signal, 3)
            },
            'weather_data': weather,
            'causal_note': "Risk includes REAL-TIME weather data + 14-day causal lag"
        }
    
    async def forecast_cases(self, district_id: str, disease: str = 'dengue', days_ahead: int = 28) -> List[Dict]:
        """
        DEEPMIND UPGRADE: Spliced Timeline Forecast
        ============================================
        
        FIRST PRINCIPLES:
        - Biological Lag: Rain on Day 0 → Cases on Day 14
        - Old Limit: We could only predict 14 days (using known past rain)
        - New Power: By forecasting FUTURE rain, we can predict 28 days ahead!
        
        SPLICED TIMELINE:
        Step A: Historical Weather (Known Past) from DB
        Step B: Forecast Weather (Predicted Future) from WeatherService
        Step C: Concat into continuous_weather DataFrame
        Step D: Shift entire timeline by 14 days (rainfall_lag_14d)
        Step E: Predict cases for T+1 to T+28
        
        SOURCE FLAGS:
        - Days 1-14: "Observed Lag" (based on rain that already fell)
        - Days 15-28: "AI Prediction (WeatherNext)" (based on forecast rain)
        """
        if district_id not in self.models:
            return self._simple_forecast(district_id, disease, days_ahead)
        
        model_info = self.models[district_id]
        if model_info.get('type') != 'prophet':
            return self._simple_forecast(district_id, disease, days_ahead)
        
        m = model_info['model']
        district = self.districts.get(district_id, {})
        
        # =========================================================================
        # STEP A: Get Historical Weather from DB (Known Past)
        # =========================================================================
        historical_weather = self.weather_df[
            self.weather_df['district_id'] == district_id
        ].sort_values('date').copy()
        
        # =========================================================================
        # STEP B: Fetch Forecast Weather from WeatherService (Predicted Future)
        # =========================================================================
        from app.services.weather_service import weather_service
        
        forecast_weather = []
        if 'lat' in district and 'lng' in district:
            try:
                # Get 14-day weather forecast
                forecast_data = await weather_service.get_forecast(
                    district['lat'], 
                    district['lng'], 
                    district_id,
                    days=14
                )
                
                for fc in forecast_data:
                    # Convert to same format as historical weather
                    forecast_weather.append({
                        'date': pd.to_datetime(fc['date']).tz_localize(None),
                        'district_id': district_id,
                        'rainfall': fc['rainfall_prediction'],
                        'temperature': fc['temperature'],
                        'humidity': fc['humidity'],
                        'rainfall_probability': fc['rainfall_probability'],
                        'source': fc['source'],
                        'is_forecast': True
                    })
            except Exception as e:
                print(f"Error fetching forecast for {district_id}: {e}")
        
        # =========================================================================
        # STEP C: Splice Timeline (History + Forecast)
        # =========================================================================
        if forecast_weather:
            forecast_df = pd.DataFrame(forecast_weather)
            # Ensure date columns are compatible (strip timezone)
            historical_weather['date'] = pd.to_datetime(historical_weather['date']).dt.tz_localize(None)
            forecast_df['date'] = pd.to_datetime(forecast_df['date']).dt.tz_localize(None)
            
            # Mark historical data
            historical_weather['is_forecast'] = False
            historical_weather['source'] = 'observed'
            historical_weather['rainfall_probability'] = 1.0  # 100% confidence in past
            
            # Concat: Historical + Forecast = Continuous Timeline
            continuous_weather = pd.concat([historical_weather, forecast_df], ignore_index=True)
            continuous_weather = continuous_weather.sort_values('date').drop_duplicates(subset=['date'], keep='last')
        else:
            continuous_weather = historical_weather.copy()
            continuous_weather['is_forecast'] = False
            continuous_weather['source'] = 'observed'
            continuous_weather['rainfall_probability'] = 1.0
        
        # =========================================================================
        # STEP D: Create Lagged Features on Spliced Timeline
        # =========================================================================
        continuous_weather['rainfall_lag_14d'] = continuous_weather['rainfall'].shift(14)
        continuous_weather['breeding_index_lag'] = (
            continuous_weather['rainfall'].shift(14) * 
            continuous_weather['humidity'].shift(14) / 100
        ).fillna(0)
        
        # =========================================================================
        # STEP E: Generate Predictions for T+1 to T+28
        # =========================================================================
        last_historical_date = historical_weather['date'].max()
        future_dates = [last_historical_date + pd.Timedelta(days=i) for i in range(1, days_ahead + 1)]
        future_df = pd.DataFrame({'ds': future_dates})
        
        # Fill regressors from spliced timeline
        regressors = []
        source_flags = []
        
        for i, date in enumerate(future_dates):
            lag_date = date - pd.Timedelta(days=14)
            
            # Look up in continuous (spliced) weather
            weather_row = continuous_weather[continuous_weather['date'] == lag_date]
            
            if not weather_row.empty:
                row = weather_row.iloc[0]
                regressors.append({
                    'rainfall_lag_14d': row.get('rainfall', 0),
                    'breeding_index_lag': row.get('rainfall', 0) * row.get('humidity', 50) / 100
                })
                
                # Determine source: Was the lagged data from forecast or observation?
                if row.get('is_forecast', False):
                    source_flags.append("AI Prediction (WeatherNext)")
                else:
                    source_flags.append("Observed Lag")
            else:
                # No data for this lag date - use fallback
                regressors.append({
                    'rainfall_lag_14d': 0,
                    'breeding_index_lag': 0
                })
                source_flags.append("No Data (Fallback)")
        
        reg_df = pd.DataFrame(regressors)
        future_df = pd.concat([future_df, reg_df], axis=1)
        
        # Run Prophet prediction
        forecast = m.predict(future_df)
        
        # =========================================================================
        # Format Output with Source Flags
        # =========================================================================
        results = []
        district_type = district.get('type', 'mixed')
        reporting_rate = 0.6 if district_type == 'urban' else 0.3 if district_type == 'rural' else 0.45
        
        for i, (_, row) in enumerate(forecast.iterrows()):
            pred = max(0, row['yhat'])
            lower = max(0, row['yhat_lower'])
            upper = max(0, row['yhat_upper'])
            
            dt = row['ds'].date() if hasattr(row['ds'], 'date') else row['ds']
            
            results.append({
                'date': dt.strftime('%Y-%m-%d'),
                'predicted': int(pred),
                'lower_bound': int(lower),
                'upper_bound': int(upper),
                'confidence': 0.95,
                'is_causal': True,
                'estimated_actual': int(pred / reporting_rate),
                'source': source_flags[i] if i < len(source_flags) else "Unknown",
                'days_ahead': i + 1
            })
        
        return results
    
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
    
    async def forecast_medicine_demand(self, district_id: str, medicine_id: str, days_ahead: int = 14) -> List[Dict]:
        """Convert case forecasts to medicine demand"""
        medicine = self.medicines.get(medicine_id)
        if not medicine:
            return []
        
        total_demand = [0.0] * days_ahead
        uncertainty = [0.0] * days_ahead
        
        for disease in medicine['diseases']:
            if disease in ['dengue', 'malaria', 'diarrhea']:
                case_forecasts = await self.forecast_cases(district_id, disease, days_ahead)
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
    
    async def calculate_safety_stock(
        self, 
        district_id: str, 
        medicine_id: str, 
        lead_time_days: int = 7,
        risk_probability: float = 0.5,
        forecast_rainfall: float = 0.0
    ) -> int:
        """
        DEEPMIND UPGRADE: Risk-Adjusted Safety Stock
        =============================================
        
        FIRST PRINCIPLES:
        - Safety Stock = Z × σ × √(Lead Time)
        - But this assumes NORMAL conditions...
        
        BLACK SWAN ADJUSTMENT:
        - If forecast indicates extreme weather (Rain > 50mm AND Probability > 80%)
        - Multiply Z-score by 1.5 ("Pre-emptive Surge Capacity")
        - Logic: "It is cheaper to overstock now than to face a flood-driven cholera spike later"
        
        Parameters:
            district_id: Target district
            medicine_id: Target medicine
            lead_time_days: Days from order to delivery
            risk_probability: Probability of adverse weather (from forecast)
            forecast_rainfall: Predicted rainfall amount (mm)
        
        Returns:
            Adjusted safety stock quantity
        """
        # Get historical demand variance
        consumption = self.consumption_df[
            (self.consumption_df['district_id'] == district_id) &
            (self.consumption_df['medicine_id'] == medicine_id)
        ]['consumption']
        
        if len(consumption) < 7:
            base_safety_stock = 100  # Minimum safety stock
        else:
            daily_std = consumption.std()
            # Base Safety Stock Formula
            base_safety_stock = self.SERVICE_LEVEL_Z * daily_std * np.sqrt(lead_time_days)
        
        # =====================================================================
        # BLACK SWAN ADJUSTMENT: Pre-emptive Surge Capacity
        # =====================================================================
        # If we forecast a high-probability extreme weather event,
        # increase safety stock to prepare for disease surge
        
        z_multiplier = 1.0  # Default: No adjustment
        
        if forecast_rainfall > 50 and risk_probability > 0.8:
            # HIGH PROBABILITY BLACK SWAN: Extreme flooding expected
            # This could trigger cholera, diarrhea, vector-borne disease spikes
            z_multiplier = 1.5
            print(f"⚠️ BLACK SWAN ALERT for {district_id}: Increasing safety stock by 50%")
        elif forecast_rainfall > 30 and risk_probability > 0.6:
            # MODERATE RISK: Significant but not extreme
            z_multiplier = 1.25
        elif forecast_rainfall > 10 and risk_probability > 0.5:
            # MILD RISK: Precautionary buffer
            z_multiplier = 1.1
        
        # Apply multiplier
        adjusted_safety_stock = base_safety_stock * z_multiplier
        
        return int(max(adjusted_safety_stock, 50))  # Minimum 50 units
    
    async def get_stock_status(self, district_id: str) -> List[Dict]:
        """Get stock with safety stock calculations"""
        district_stock = self.stock_df[self.stock_df['district_id'] == district_id]
        
        results = []
        for _, row in district_stock.iterrows():
            medicine = self.medicines.get(row['medicine_id'], {})
            
            # Get 14-day demand forecast
            demand_forecast = await self.forecast_medicine_demand(district_id, row['medicine_id'], 14)
            total_14d_demand = sum(f['predicted_demand'] for f in demand_forecast)
            total_uncertainty = sum(f['uncertainty'] for f in demand_forecast)
            
            # Calculate proper safety stock
            safety_stock = await self.calculate_safety_stock(district_id, row['medicine_id'])
            
            current_stock = row['quantity']
            
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
            
            # Compute days until expiry from expiry_date
            expiry_date = row['expiry_date']
            if isinstance(expiry_date, str):
                expiry_date = datetime.strptime(expiry_date, '%Y-%m-%d').date()
            elif hasattr(expiry_date, 'date'):
                expiry_date = expiry_date.date()
            days_until_expiry = (expiry_date - datetime.now().date()).days
            
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
                'days_until_expiry': int(days_until_expiry)
            })
        
        return results
    
    async def optimize_network_transfers(self) -> List[Dict]:
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
                stock_status = await self.get_stock_status(district_id)
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
    
    async def get_recommendations(self, district_id: str) -> List[Dict]:
        """Generate recommendations using network-aware logic"""
        stock_status = await self.get_stock_status(district_id)
        risk = await self.calculate_risk_score(district_id)
        network_plan = await self.optimize_network_transfers()
        
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
