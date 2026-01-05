"""
MedPredict AI - Weather Service (DeepMind Upgrade)
==================================================
FIRST PRINCIPLES:
- Weather forecasts allow us to PREDICT breeding conditions before they happen
- By knowing rain WILL fall in 7 days, we can predict cases in 21 days (7 + 14 biological lag)
- This extends our response window from 14 days to 28 days

DUAL STRATEGY:
1. Primary: Google Weather API (if GOOGLE_WEATHER_API_KEY exists) - Enterprise grade
2. Fallback: Open-Meteo (free) - Perfect for hackathon demos
"""

import os
import httpx
import json
import time
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Load env from parent directory if needed
env_path = Path(__file__).parent.parent.parent / '.env'
load_dotenv(env_path)

# API Keys
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")
GOOGLE_WEATHER_API_KEY = os.getenv("GOOGLE_WEATHER_API_KEY")  # Future: Google Maps Weather API

# API URLs
OPENWEATHER_BASE_URL = "https://api.openweathermap.org/data/2.5"
OPEN_METEO_BASE_URL = "https://api.open-meteo.com/v1/forecast"

# Cache Config
CACHE_FILE = Path(__file__).parent.parent.parent / "data" / "weather_cache.json"
CACHE_TTL = 3600  # 1 hour for current weather
FORECAST_CACHE_TTL = 21600  # 6 hours for forecasts (they don't change as often)


class WeatherService:
    """
    Hybrid Weather Service: Current + Forecast
    
    This service provides both:
    1. get_current_weather() - Real-time conditions (OpenWeatherMap)
    2. get_forecast() - 14-day predictions (Open-Meteo / Google Weather)
    
    The combination enables 28-day disease prediction windows.
    """
    
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=15.0)
        self.cache = self._load_cache()
        
        if not OPENWEATHER_API_KEY:
            print("WARNING: No OpenWeatherMap API Key found!")
        if GOOGLE_WEATHER_API_KEY:
            print("INFO: Google Weather API Key detected - using enterprise forecasts")
        else:
            print("INFO: Using Open-Meteo for weather forecasts (free tier)")

    def _load_cache(self) -> Dict:
        if CACHE_FILE.exists():
            try:
                with open(CACHE_FILE) as f:
                    return json.load(f)
            except:
                return {}
        return {}

    def _save_cache(self):
        CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(CACHE_FILE, 'w') as f:
            json.dump(self.cache, f)

    # =========================================================================
    # CURRENT WEATHER (Existing functionality - OpenWeatherMap)
    # =========================================================================
    
    async def get_current_weather(self, lat: float, lon: float, district_id: str) -> Dict:
        """
        Get current weather for a location (Real Data from OpenWeatherMap)
        """
        cache_key = f"current_{district_id}"
        now = time.time()
        
        # Check cache
        if cache_key in self.cache:
            entry = self.cache[cache_key]
            if now - entry['timestamp'] < CACHE_TTL:
                return entry['data']
        
        if not OPENWEATHER_API_KEY:
            return self._get_fallback_weather()

        try:
            url = f"{OPENWEATHER_BASE_URL}/weather"
            params = {
                "lat": lat,
                "lon": lon,
                "appid": OPENWEATHER_API_KEY,
                "units": "metric"
            }
            
            response = await self.client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            weather_data = {
                "temperature": data['main']['temp'],
                "humidity": data['main']['humidity'],
                "rainfall": data.get('rain', {}).get('1h', 0),
                "condition": data['weather'][0]['main']
            }
            
            # Update cache
            self.cache[cache_key] = {
                "timestamp": now,
                "data": weather_data
            }
            self._save_cache()
            
            return weather_data
            
        except Exception as e:
            print(f"Error fetching current weather for {district_id}: {e}")
            return self._get_fallback_weather()

    # =========================================================================
    # WEATHER FORECAST (NEW - DeepMind Upgrade)
    # =========================================================================
    
    async def get_forecast(self, lat: float, lon: float, district_id: str, days: int = 14) -> List[Dict]:
        """
        Get 14-day weather forecast (Simulating WeatherNext/GraphCast behavior)
        
        FIRST PRINCIPLES:
        - We need FUTURE weather to predict FUTURE disease outbreaks
        - Rainfall in 7 days → Mosquito breeding in 14 days → Cases in 21 days
        - This forecast extends our prediction horizon from 14 to 28 days
        
        DUAL STRATEGY:
        1. If GOOGLE_WEATHER_API_KEY exists → Use Google Weather API (Enterprise)
        2. Else → Use Open-Meteo (Free, perfect for hackathon)
        
        Returns:
            List of dicts with: {date, rainfall_prediction, rainfall_probability, 
                                 temperature, humidity, source}
        """
        cache_key = f"forecast_{district_id}_{days}"
        now = time.time()
        
        # Check cache (longer TTL for forecasts)
        if cache_key in self.cache:
            entry = self.cache[cache_key]
            if now - entry['timestamp'] < FORECAST_CACHE_TTL:
                return entry['data']
        
        # DUAL STRATEGY: Choose API based on available keys
        if GOOGLE_WEATHER_API_KEY:
            forecast = await self._fetch_google_forecast(lat, lon, days)
        else:
            forecast = await self._fetch_open_meteo_forecast(lat, lon, days)
        
        # Cache the result
        if forecast:
            self.cache[cache_key] = {
                "timestamp": now,
                "data": forecast
            }
            self._save_cache()
        
        return forecast
    
    async def _fetch_google_forecast(self, lat: float, lon: float, days: int) -> List[Dict]:
        """
        Fetch weather forecast from Google Weather API (Enterprise Grade)
        
        Uses the Google Maps Weather API v1:
        - Endpoint: https://weather.googleapis.com/v1/forecast/days:lookup
        - Provides up to 10 days of daily forecasts
        - AI-powered hyperlocal weather predictions
        """
        try:
            # Google Weather API endpoint
            url = "https://weather.googleapis.com/v1/forecast/days:lookup"
            
            params = {
                "key": GOOGLE_WEATHER_API_KEY,
                "location.latitude": lat,
                "location.longitude": lon,
                "days": min(days, 10),  # Google supports up to 10 days
                "unitsSystem": "METRIC"
            }
            
            response = await self.client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            forecast = []
            forecast_days = data.get('forecastDays', [])
            
            for day_data in forecast_days:
                # Extract date
                date_info = day_data.get('displayDate', {})
                date_str = f"{date_info.get('year', 2026)}-{date_info.get('month', 1):02d}-{date_info.get('day', 1):02d}"
                
                # Extract daytime forecast (primary)
                daytime = day_data.get('daytimeForecast', {})
                nighttime = day_data.get('nighttimeForecast', {})
                
                # Precipitation
                precip = daytime.get('precipitation', {})
                rainfall = precip.get('qpf', {}).get('quantity', 0)  # Quantitative Precipitation Forecast
                rain_probability = precip.get('probability', {}).get('percent', 0) / 100.0
                
                # Temperature (use max/min from the day)
                temp_max = day_data.get('maxTemperature', {}).get('degrees', 30)
                temp_min = day_data.get('minTemperature', {}).get('degrees', 20)
                temperature = (temp_max + temp_min) / 2
                
                # Humidity
                humidity_day = daytime.get('relativeHumidity', 50)
                humidity_night = nighttime.get('relativeHumidity', 50)
                humidity = (humidity_day + humidity_night) / 2
                
                forecast.append({
                    "date": date_str,
                    "rainfall_prediction": rainfall,
                    "rainfall_probability": rain_probability if rain_probability > 0 else 0.8,
                    "temperature": round(temperature, 1),
                    "humidity": round(humidity, 1),
                    "source": "google-weather-api",
                    "is_forecast": True
                })
            
            if forecast:
                print(f"✅ Google Weather API: Retrieved {len(forecast)} days of forecast")
                return forecast
            else:
                print("⚠️ Google Weather API returned empty forecast, falling back to Open-Meteo")
                return await self._fetch_open_meteo_forecast(lat, lon, days)
                
        except httpx.HTTPStatusError as e:
            print(f"❌ Google Weather API HTTP Error {e.response.status_code}: {e.response.text[:200]}")
            print("Falling back to Open-Meteo...")
            return await self._fetch_open_meteo_forecast(lat, lon, days)
        except Exception as e:
            print(f"❌ Google Weather API Error: {e}")
            print("Falling back to Open-Meteo...")
            return await self._fetch_open_meteo_forecast(lat, lon, days)
    
    async def _fetch_open_meteo_forecast(self, lat: float, lon: float, days: int) -> List[Dict]:
        """
        Fetch weather forecast from Open-Meteo (FREE API - No key required!)
        
        Open-Meteo provides:
        - 16-day forecast
        - Hourly/Daily resolution
        - Precipitation, temperature, humidity
        - Perfect for hackathon demos
        
        Note: Open-Meteo is deterministic (single forecast), so we simulate
        probability as 0.8 to mock ensemble behavior like WeatherNext.
        """
        try:
            params = {
                "latitude": lat,
                "longitude": lon,
                "daily": ["precipitation_sum", "temperature_2m_max", "temperature_2m_min", 
                          "relative_humidity_2m_max", "relative_humidity_2m_min"],
                "timezone": "auto",
                "forecast_days": min(days, 16)  # Open-Meteo supports up to 16 days
            }
            
            response = await self.client.get(OPEN_METEO_BASE_URL, params=params)
            response.raise_for_status()
            data = response.json()
            
            daily = data.get('daily', {})
            dates = daily.get('time', [])
            precip = daily.get('precipitation_sum', [])
            temp_max = daily.get('temperature_2m_max', [])
            temp_min = daily.get('temperature_2m_min', [])
            humidity_max = daily.get('relative_humidity_2m_max', [])
            humidity_min = daily.get('relative_humidity_2m_min', [])
            
            forecast = []
            for i, date in enumerate(dates):
                # Calculate averages
                temp = (temp_max[i] + temp_min[i]) / 2 if i < len(temp_max) else 25.0
                humidity = (humidity_max[i] + humidity_min[i]) / 2 if i < len(humidity_max) else 50.0
                rainfall = precip[i] if i < len(precip) else 0.0
                
                # Simulate probability (Open-Meteo is deterministic)
                # Higher rainfall = higher confidence in the prediction
                if rainfall > 20:
                    probability = 0.9  # High confidence heavy rain
                elif rainfall > 5:
                    probability = 0.8  # Good confidence moderate rain
                elif rainfall > 0:
                    probability = 0.7  # Moderate confidence light rain
                else:
                    probability = 0.8  # Default confidence for dry weather
                
                forecast.append({
                    "date": date,
                    "rainfall_prediction": rainfall,
                    "rainfall_probability": probability,
                    "temperature": round(temp, 1),
                    "humidity": round(humidity, 1),
                    "source": "open-meteo",
                    "is_forecast": True
                })
            
            return forecast
            
        except Exception as e:
            print(f"Error fetching Open-Meteo forecast: {e}")
            return self._get_fallback_forecast(days)
    
    def _get_fallback_forecast(self, days: int) -> List[Dict]:
        """
        Fallback forecast if all APIs fail
        Uses seasonal averages for Rajasthan
        """
        forecast = []
        today = datetime.now().date()
        
        for i in range(days):
            forecast_date = today + timedelta(days=i+1)
            
            # Seasonal simulation for Rajasthan
            month = forecast_date.month
            if month in [7, 8, 9]:  # Monsoon
                rainfall = 15.0
                probability = 0.7
            elif month in [6, 10]:  # Pre/Post monsoon
                rainfall = 5.0
                probability = 0.5
            else:  # Dry season
                rainfall = 0.0
                probability = 0.8
            
            forecast.append({
                "date": forecast_date.strftime("%Y-%m-%d"),
                "rainfall_prediction": rainfall,
                "rainfall_probability": probability,
                "temperature": 30.0,
                "humidity": 50.0,
                "source": "fallback",
                "is_forecast": True
            })
        
        return forecast

    def _get_fallback_weather(self) -> Dict:
        """Fallback for current weather if API fails"""
        return {
            "temperature": 30.0,
            "humidity": 50.0,
            "rainfall": 0.0,
            "condition": "Clear"
        }

    async def close(self):
        await self.client.aclose()


# Global instance
weather_service = WeatherService()
