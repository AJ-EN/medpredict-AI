
import sys
from pathlib import Path
import json
import pandas as pd
from sqlmodel import Session, select
from datetime import datetime

# Add parent directory to path to import app modules
sys.path.append(str(Path(__file__).parent.parent))

from app.db.database import engine, create_db_and_tables
from app.db.models import District, Medicine, Stock, WeatherLog, DiseaseCase

DATA_DIR = Path(__file__).parent.parent / "data"

def ingest_data():
    print("Creating tables...")
    create_db_and_tables()
    
    with Session(engine) as session:
        # 1. Ingest Config (Districts & Medicines)
        print("Ingesting config.json...")
        with open(DATA_DIR / "config.json") as f:
            config = json.load(f)
            
        # Districts
        for d in config['districts']:
            district = District(
                id=d['id'],
                name=d['name'],
                population=d['population'],
                type=d['type'],
                lat=d['lat'],
                lng=d['lng']
            )
            session.merge(district)
            
        # Medicines
        for m in config['medicines']:
            medicine = Medicine(
                id=m['id'],
                name=m['name'],
                category=m['category'],
                unit=m['unit'],
                shelf_life_days=m['shelf_life_days'],
                cold_chain=m['cold_chain'],
                prescription_rate=m['prescription_rate'],
                units_per_case=m['units_per_case']
            )
            session.merge(medicine)
        
        session.commit()
        
        # 2. Ingest CSVs using Pandas
        print("Ingesting CSV data...")
        
        # Stock
        if (DATA_DIR / "synthetic_stock.csv").exists():
            df = pd.read_csv(DATA_DIR / "synthetic_stock.csv")
            for _, row in df.iterrows():
                # Calculate expiry date from days_until_expiry
                expiry = datetime.now().date() + pd.Timedelta(days=row['days_until_expiry'])
                
                stock = Stock(
                    district_id=row['district_id'],
                    medicine_id=row['medicine_id'],
                    quantity=row['current_stock'],
                    batch_id=f"BATCH-{row['district_id']}-{datetime.now().year}",
                    expiry_date=expiry
                )
                session.add(stock)
        
        # Cases
        if (DATA_DIR / "synthetic_cases.csv").exists():
            df = pd.read_csv(DATA_DIR / "synthetic_cases.csv")
            for _, row in df.iterrows():
                 # Handle melted wide format if needed OR assuming long format?
                 # Looking at synthetic.py, it likely saves in long format or we need to check.
                 # Let's check the CSV format first in the next step if this fails, but usually standard is long.
                 # Actually, synthetic.py usually saves generated data. Let's assume standard columns.
                 # Wait, synthetic.py usually generates `date, district_id, dengue_cases, ...`
                 
                 date_val = datetime.strptime(row['date'], '%Y-%m-%d').date()
                 district_id = row['district_id']
                 
                 for disease in ['dengue', 'malaria', 'diarrhea']:
                     col = f"{disease}_cases"
                     if col in df.columns:
                         case = DiseaseCase(
                             district_id=district_id,
                             date=date_val,
                             disease=disease,
                             count=row[col]
                         )
                         session.add(case)

        # Weather
        if (DATA_DIR / "synthetic_weather.csv").exists():
            df = pd.read_csv(DATA_DIR / "synthetic_weather.csv")
            for _, row in df.iterrows():
                log = WeatherLog(
                    district_id=row['district_id'],
                    date=datetime.strptime(row['date'], '%Y-%m-%d').date(),
                    temperature=row['temperature'],
                    rainfall=row['rainfall'],
                    humidity=row['humidity'],
                    source='synthetic'
                )
                session.add(log)
        
        session.commit()
        print("Data ingestion complete!")

if __name__ == "__main__":
    ingest_data()
