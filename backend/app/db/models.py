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


# --- TRANSFER VERIFICATION PROTOCOL ---

class Transfer(SQLModel, table=True):
    """
    Medicine transfer between districts with cryptographic chain of custody.
    Requires 3-party verification: Sender → Transporter → Receiver
    """
    id: str = Field(primary_key=True)  # UUID
    
    # What is being transferred
    medicine_id: str = Field(foreign_key="medicine.id")
    quantity: int
    
    # From → To
    from_district_id: str = Field(foreign_key="district.id")
    to_district_id: str = Field(foreign_key="district.id")
    
    # Status: created → picked_up → in_transit → delivered → verified / disputed
    status: str = Field(default="created")
    priority: str = Field(default="normal")  # normal, urgent, critical
    
    # --- SENDER (Step 1) ---
    created_at: datetime = Field(default_factory=datetime.now)
    created_by: str  # User/Officer ID who initiated
    sender_signature: Optional[str] = None  # SHA256 hash of (items + qty + timestamp)
    sender_photo_hash: Optional[str] = None  # Hash of photo evidence
    sender_notes: Optional[str] = None
    
    # --- TRANSPORTER (Step 2) ---
    pickup_at: Optional[datetime] = None
    transporter_id: Optional[str] = None  # Vehicle/Driver ID
    transporter_signature: Optional[str] = None
    pickup_location_lat: Optional[float] = None
    pickup_location_lng: Optional[float] = None
    expected_delivery_at: Optional[datetime] = None
    
    # --- RECEIVER (Step 3) ---
    delivered_at: Optional[datetime] = None
    receiver_id: Optional[str] = None
    receiver_signature: Optional[str] = None
    receiver_photo_hash: Optional[str] = None
    delivery_location_lat: Optional[float] = None
    delivery_location_lng: Optional[float] = None
    received_quantity: Optional[int] = None
    receiver_notes: Optional[str] = None
    
    # --- VERIFICATION ---
    verification_hash: Optional[str] = None  # Final integrity hash combining all signatures
    is_verified: bool = Field(default=False)
    verified_at: Optional[datetime] = None
    
    # --- ANOMALY DETECTION ---
    has_discrepancy: bool = Field(default=False)
    discrepancy_type: Optional[str] = None  # quantity_mismatch, time_violation, signature_missing
    discrepancy_notes: Optional[str] = None
    
    # Relationships
    items: List["TransferItem"] = Relationship(back_populates="transfer")


class TransferItem(SQLModel, table=True):
    """
    Individual medicine batches within a transfer.
    Each batch has a unique QR code that must be scanned at sender and receiver.
    """
    id: Optional[int] = Field(default=None, primary_key=True)
    transfer_id: str = Field(foreign_key="transfer.id")
    
    batch_qr_code: str  # Unique identifier for this batch
    batch_id: str  # Reference to Stock.batch_id
    quantity: int
    expiry_date: Optional[date] = None
    
    # Scanning verification
    scanned_at_sender: bool = Field(default=False)
    sender_scan_time: Optional[datetime] = None
    
    scanned_at_receiver: bool = Field(default=False)
    receiver_scan_time: Optional[datetime] = None
    
    # Condition on receipt
    condition_on_receipt: Optional[str] = None  # good, damaged, expired
    
    transfer: Transfer = Relationship(back_populates="items")

