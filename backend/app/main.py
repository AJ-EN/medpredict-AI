"""
MedPredict AI - FastAPI Backend
Main application entry point
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import json
from pathlib import Path

from app.routers import forecast, alerts, recommendations, stock, transfers
from app.db.database import create_db_and_tables
from app.data.synthetic import generate_all_data
from app.models.forecaster import DemandForecaster

# Global state
forecaster = None
config = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize models and data on startup"""
    global forecaster, config
    
    # Load config
    config_path = Path(__file__).parent.parent / "data" / "config.json"
    with open(config_path) as f:
        config = json.load(f)
    
    # Initialize database tables (for Transfer Verification Protocol)
    create_db_and_tables()
    
    # Generate synthetic data if not exists
    data_dir = Path(__file__).parent.parent / "data"
    if not (data_dir / "synthetic_cases.csv").exists():
        print("Generating synthetic data...")
        generate_all_data(config, data_dir)
    
    # Initialize forecaster
    forecaster = DemandForecaster(config, data_dir)
    print("MedPredict AI Backend Ready!")
    
    yield
    
    # Cleanup
    print("Shutting down...")
    from app.services.weather_service import weather_service
    await weather_service.close()


app = FastAPI(
    title="MedPredict AI",
    description="AI-Based Medicine Demand Forecasting for Public Health Emergencies",
    version="1.0.0",
    lifespan=lifespan
)

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(forecast.router, prefix="/api/forecast", tags=["forecast"])
app.include_router(alerts.router, prefix="/api/alerts", tags=["alerts"])
app.include_router(recommendations.router, prefix="/api/recommendations", tags=["recommendations"])
app.include_router(stock.router, prefix="/api/stock", tags=["stock"])
app.include_router(transfers.router, prefix="/api/transfers", tags=["transfers"])


@app.get("/")
async def root():
    return {
        "name": "MedPredict AI",
        "status": "operational",
        "version": "1.0.0"
    }


@app.get("/api/config")
async def get_config():
    """Get districts and medicines configuration"""
    return config


@app.get("/api/health")
async def health_check():
    return {"status": "healthy", "forecaster_ready": forecaster is not None}
