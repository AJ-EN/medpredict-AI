"""
Synthetic Data Generator for MedPredict AI
Generates realistic disease outbreak and medicine consumption data
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
import json


def generate_weather_data(districts: list, start_date: str, days: int = 365) -> pd.DataFrame:
    """
    Generate synthetic weather data with realistic patterns for Rajasthan
    Monsoon: July-September, Winter: November-February, Summer: March-June
    """
    np.random.seed(42)
    
    dates = pd.date_range(start=start_date, periods=days, freq='D')
    records = []
    
    for district in districts:
        for date in dates:
            month = date.month
            
            # Temperature patterns (Rajasthan is hot and dry)
            if month in [11, 12, 1, 2]:  # Winter
                base_temp = 18 + np.random.normal(0, 3)
            elif month in [3, 4, 5, 6]:  # Summer
                base_temp = 38 + np.random.normal(0, 4)
            else:  # Monsoon
                base_temp = 30 + np.random.normal(0, 3)
            
            # Rainfall (mostly in monsoon)
            if month in [7, 8, 9]:  # Monsoon
                rainfall = max(0, np.random.exponential(15))
                # Some districts get more rain
                if district['type'] == 'urban':
                    rainfall *= 1.2
            else:
                rainfall = max(0, np.random.exponential(1)) if np.random.random() > 0.85 else 0
            
            # Humidity follows rainfall
            humidity = min(95, max(20, 40 + rainfall * 2 + np.random.normal(0, 10)))
            
            records.append({
                'date': date,
                'district_id': district['id'],
                'temperature': round(base_temp, 1),
                'rainfall': round(rainfall, 1),
                'humidity': round(humidity, 1)
            })
    
    return pd.DataFrame(records)


def generate_case_data(districts: list, weather_df: pd.DataFrame) -> pd.DataFrame:
    """
    Generate synthetic disease cases correlated with weather
    - Dengue: peaks with monsoon (7-14 day lag from rainfall)
    - Malaria: similar but longer lag
    - Diarrhea: inversely related to rainfall (water scarcity in summer)
    """
    np.random.seed(43)
    
    # Add lagged features to weather data
    weather_df = weather_df.copy()
    
    records = []
    
    for district in districts:
        district_weather = weather_df[weather_df['district_id'] == district['id']].copy()
        district_weather = district_weather.sort_values('date')
        
        # Calculate rolling features
        district_weather['rainfall_7d'] = district_weather['rainfall'].rolling(7, min_periods=1).sum()
        district_weather['rainfall_14d'] = district_weather['rainfall'].rolling(14, min_periods=1).sum()
        district_weather['temp_7d_avg'] = district_weather['temperature'].rolling(7, min_periods=1).mean()
        
        pop_factor = district['population'] / 1000000  # Cases scale with population
        
        for _, row in district_weather.iterrows():
            date = row['date']
            
            # Dengue: peaks when temp is 25-30°C and after rainfall
            temp_factor = np.exp(-((row['temp_7d_avg'] - 27) ** 2) / 50)
            rain_factor = min(row['rainfall_14d'] / 100, 2.0)
            dengue_base = 5 * pop_factor * temp_factor * rain_factor
            dengue_cases = max(0, int(dengue_base * np.random.lognormal(0, 0.5)))
            
            # Malaria: similar pattern
            malaria_base = 3 * pop_factor * temp_factor * rain_factor * 0.7
            malaria_cases = max(0, int(malaria_base * np.random.lognormal(0, 0.6)))
            
            # Diarrhea: higher in summer (water scarcity), also monsoon (contamination)
            if row['temperature'] > 35:  # Summer peak
                diarrhea_base = 15 * pop_factor
            elif row['rainfall_7d'] > 30:  # Monsoon contamination
                diarrhea_base = 12 * pop_factor
            else:
                diarrhea_base = 5 * pop_factor
            diarrhea_cases = max(0, int(diarrhea_base * np.random.lognormal(0, 0.4)))
            
            records.append({
                'date': date,
                'district_id': district['id'],
                'dengue_cases': dengue_cases,
                'malaria_cases': malaria_cases,
                'diarrhea_cases': diarrhea_cases,
                'total_fever_cases': dengue_cases + malaria_cases + int(np.random.poisson(10 * pop_factor))
            })
    
    return pd.DataFrame(records)


def generate_consumption_data(cases_df: pd.DataFrame, medicines: list) -> pd.DataFrame:
    """
    Generate medicine consumption based on cases and treatment protocols
    """
    np.random.seed(44)
    
    healthcare_seeking_rate = 0.6  # 60% of cases seek public healthcare
    
    records = []
    
    for _, row in cases_df.iterrows():
        for medicine in medicines:
            # Calculate demand based on which diseases this medicine treats
            demand = 0
            
            if 'dengue' in medicine['diseases']:
                demand += row['dengue_cases'] * medicine['prescription_rate'] * medicine['units_per_case']
            
            if 'malaria' in medicine['diseases']:
                demand += row['malaria_cases'] * medicine['prescription_rate'] * medicine['units_per_case']
            
            if 'diarrhea' in medicine['diseases']:
                demand += row['diarrhea_cases'] * medicine['prescription_rate'] * medicine['units_per_case']
            
            if 'fever' in medicine['diseases']:
                demand += row['total_fever_cases'] * 0.5 * medicine['prescription_rate'] * medicine['units_per_case']
            
            # Apply healthcare seeking rate and add noise
            actual_consumption = int(demand * healthcare_seeking_rate * np.random.uniform(0.8, 1.2))
            
            records.append({
                'date': row['date'],
                'district_id': row['district_id'],
                'medicine_id': medicine['id'],
                'consumption': max(0, actual_consumption)
            })
    
    return pd.DataFrame(records)


def generate_stock_data(districts: list, medicines: list) -> pd.DataFrame:
    """
    Generate current stock levels for each district and medicine
    """
    np.random.seed(45)
    
    records = []
    
    for district in districts:
        pop_factor = district['population'] / 1000000
        
        for medicine in medicines:
            # Stock based on population and 30-day average consumption
            avg_daily_consumption = 50 * pop_factor
            safety_stock = avg_daily_consumption * 14  # 2 weeks safety stock
            current_stock = int(safety_stock * np.random.uniform(0.3, 1.5))
            
            # Calculate days until expiry (random)
            days_until_expiry = np.random.randint(30, min(180, medicine['shelf_life_days']))
            
            records.append({
                'district_id': district['id'],
                'medicine_id': medicine['id'],
                'current_stock': current_stock,
                'safety_stock': int(safety_stock),
                'days_until_expiry': days_until_expiry,
                'last_order_date': (datetime.now() - timedelta(days=np.random.randint(7, 30))).strftime('%Y-%m-%d')
            })
    
    return pd.DataFrame(records)


def generate_all_data(config: dict, output_dir: Path):
    """Generate all synthetic datasets and save to CSV"""
    
    districts = config['districts']
    medicines = config['medicines']
    
    # Generate data for past year
    start_date = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')
    
    print("Generating weather data...")
    weather_df = generate_weather_data(districts, start_date, days=365)
    weather_df.to_csv(output_dir / 'synthetic_weather.csv', index=False)
    
    print("Generating case data...")
    cases_df = generate_case_data(districts, weather_df)
    cases_df.to_csv(output_dir / 'synthetic_cases.csv', index=False)
    
    print("Generating consumption data...")
    consumption_df = generate_consumption_data(cases_df, medicines)
    consumption_df.to_csv(output_dir / 'synthetic_consumption.csv', index=False)
    
    print("Generating stock data...")
    stock_df = generate_stock_data(districts, medicines)
    stock_df.to_csv(output_dir / 'synthetic_stock.csv', index=False)
    
    print(f"Data generation complete! Files saved to {output_dir}")
    
    return {
        'weather': weather_df,
        'cases': cases_df,
        'consumption': consumption_df,
        'stock': stock_df
    }


if __name__ == "__main__":
    # Test data generation
    config_path = Path(__file__).parent.parent.parent / "data" / "config.json"
    with open(config_path) as f:
        config = json.load(f)
    
    output_dir = Path(__file__).parent.parent.parent / "data"
    generate_all_data(config, output_dir)
