"""
Forecast API Router
"""

from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from datetime import datetime

router = APIRouter()


def get_forecaster():
    """Get forecaster from app state"""
    from app.main import forecaster
    if forecaster is None:
        raise HTTPException(status_code=503, detail="Forecaster not initialized")
    return forecaster


@router.get("/state")
async def get_state_forecast(days_ahead: int = Query(14, ge=1, le=30)):
    """Get forecast overview for all districts"""
    forecaster = get_forecaster()
    
    results = {}
    for district_id in forecaster.districts.keys():
        risk = await forecaster.calculate_risk_score(district_id)
        case_forecast = await forecaster.forecast_cases(district_id, 'dengue', days_ahead)
        
        # Calculate total predicted cases
        total_cases = sum(f['predicted'] for f in case_forecast)
        peak_day = max(case_forecast, key=lambda x: x['predicted']) if case_forecast else None
        
        results[district_id] = {
            'district_name': forecaster.districts[district_id]['name'],
            'risk_level': risk['level'],
            'risk_score': risk['score'],
            'total_predicted_cases': int(total_cases),
            'peak_day': peak_day['date'] if peak_day else None,
            'peak_cases': int(peak_day['predicted']) if peak_day else 0
        }
    
    return {
        'generated_at': datetime.now().isoformat(),
        'days_ahead': days_ahead,
        'districts': results
    }


@router.get("/{district_id}")
async def get_district_forecast(
    district_id: str,
    disease: str = Query('dengue', description="Disease to forecast"),
    days_ahead: int = Query(28, ge=1, le=35)  # DeepMind Upgrade: Extended to 28 days
):
    """Get detailed case forecast for a district"""
    forecaster = get_forecaster()
    
    if district_id not in forecaster.districts:
        raise HTTPException(status_code=404, detail=f"District {district_id} not found")
    
    case_forecast = await forecaster.forecast_cases(district_id, disease, days_ahead)
    risk = await forecaster.calculate_risk_score(district_id)
    
    return {
        'district_id': district_id,
        'district_name': forecaster.districts[district_id]['name'],
        'disease': disease,
        'risk': risk,
        'forecast': case_forecast,
        'generated_at': datetime.now().isoformat()
    }


@router.get("/{district_id}/medicine/{medicine_id}")
async def get_medicine_forecast(
    district_id: str,
    medicine_id: str,
    days_ahead: int = Query(14, ge=1, le=30)
):
    """Get medicine demand forecast for a district"""
    forecaster = get_forecaster()
    
    if district_id not in forecaster.districts:
        raise HTTPException(status_code=404, detail=f"District {district_id} not found")
    
    if medicine_id not in forecaster.medicines:
        raise HTTPException(status_code=404, detail=f"Medicine {medicine_id} not found")
    
    demand_forecast = await forecaster.forecast_medicine_demand(district_id, medicine_id, days_ahead)
    
    return {
        'district_id': district_id,
        'medicine_id': medicine_id,
        'medicine_name': forecaster.medicines[medicine_id]['name'],
        'forecast': demand_forecast,
        'total_predicted': sum(f['predicted_demand'] for f in demand_forecast),
        'generated_at': datetime.now().isoformat()
    }


@router.get("/{district_id}/all-medicines")
async def get_all_medicine_forecasts(
    district_id: str,
    days_ahead: int = Query(14, ge=1, le=30)
):
    """Get demand forecast for all medicines in a district"""
    forecaster = get_forecaster()
    
    if district_id not in forecaster.districts:
        raise HTTPException(status_code=404, detail=f"District {district_id} not found")
    
    results = {}
    for medicine_id in forecaster.medicines.keys():
        demand_forecast = await forecaster.forecast_medicine_demand(district_id, medicine_id, days_ahead)
        results[medicine_id] = {
            'name': forecaster.medicines[medicine_id]['name'],
            'forecast': demand_forecast,
            'total_predicted': sum(f['predicted_demand'] for f in demand_forecast)
        }
    
    return {
        'district_id': district_id,
        'medicines': results,
        'generated_at': datetime.now().isoformat()
    }
