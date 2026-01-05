
from typing import Optional, List
from sqlmodel import Field, SQLModel, Relationship
from datetime import date, datetime

# --- CORE ENTITIES ---

class District(SQLModel, table=True):
    id: str = Field(primary_key=True)
    name: str
    population: int
    type: str  # urban, rural, mixed
    lat: float
    lng: float
    
    # Relationships
    stocks: List["Stock"] = Relationship(back_populates="district")
    weather_logs: List["WeatherLog"] = Relationship(back_populates="district")
    cases: List["DiseaseCase"] = Relationship(back_populates="district")


class Medicine(SQLModel, table=True):
    id: str = Field(primary_key=True)
    name: str
    category: str
    unit: str
    shelf_life_days: int
    cold_chain: bool
    prescription_rate: float
    units_per_case: int
    
    stocks: List["Stock"] = Relationship(back_populates="medicine")


# --- DYNAMIC DATA ---

class Stock(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    district_id: str = Field(foreign_key="district.id")
    medicine_id: str = Field(foreign_key="medicine.id")
    quantity: int
    batch_id: str
    expiry_date: date
    updated_at: datetime = Field(default_factory=datetime.now)
    
    district: District = Relationship(back_populates="stocks")
    medicine: Medicine = Relationship(back_populates="stocks")


class WeatherLog(SQLModel, table=True):
    """Stores BOTH historical (synthetic) and real-time weather"""
    id: Optional[int] = Field(default=None, primary_key=True)
    district_id: str = Field(foreign_key="district.id")
    date: date
    
    temperature: float
    rainfall: float
    humidity: float
    
    # New fields for production
    is_forecast: bool = Field(default=False)
    source: str = Field(default="synthetic")  # 'synthetic' or 'openweathermap'
    
    district: District = Relationship(back_populates="weather_logs")


class DiseaseCase(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    district_id: str = Field(foreign_key="district.id")
    date: date
    disease: str  # dengue, malaria, etc.
    count: int
    
    district: District = Relationship(back_populates="cases")
