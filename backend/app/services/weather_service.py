
import os
import httpx
import json
import time
from pathlib import Path
from typing import Dict, Optional, Tuple
from dotenv import load_dotenv

# Load env from parent directory if needed
env_path = Path(__file__).parent.parent.parent / '.env'
load_dotenv(env_path)

API_KEY = os.getenv("OPENWEATHER_API_KEY")
BASE_URL = "https://api.openweathermap.org/data/2.5"
CACHE_FILE = Path(__file__).parent.parent.parent / "data" / "weather_cache.json"
CACHE_TTL = 3600  # 1 hour

class WeatherService:
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=10.0)
        self.cache = self._load_cache()
        
        if not API_KEY:
            print("WARNING: No OpenWeatherMap API Key found!")

    def _load_cache(self) -> Dict:
        if CACHE_FILE.exists():
            try:
                with open(CACHE_FILE) as f:
                    return json.load(f)
            except:
                return {}
        return {}

    def _save_cache(self):
        # Ensure directory exists
        CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(CACHE_FILE, 'w') as f:
            json.dump(self.cache, f)

    async def get_current_weather(self, lat: float, lon: float, district_id: str) -> Dict:
        """
        Get current weather for a location (Real Data)
        """
        cache_key = f"current_{district_id}"
        now = time.time()
        
        # Check cache
        if cache_key in self.cache:
            entry = self.cache[cache_key]
            if now - entry['timestamp'] < CACHE_TTL:
                return entry['data']
        
        if not API_KEY:
            # Fallback for dev without key
            return self._get_fallback_weather()

        try:
            url = f"{BASE_URL}/weather"
            params = {
                "lat": lat,
                "lon": lon,
                "appid": API_KEY,
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
            print(f"Error fetching weather for {district_id}: {e}")
            return self._get_fallback_weather()

    def _get_fallback_weather(self):
        """Fallback if API fails"""
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
