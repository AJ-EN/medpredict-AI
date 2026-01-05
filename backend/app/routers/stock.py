"""
Stock API Router
"""

from fastapi import APIRouter, HTTPException
from datetime import datetime

router = APIRouter()


def get_forecaster():
    from app.main import forecaster
    return forecaster


@router.get("/state")
async def get_state_stock_overview():
    """Get stock overview for entire state"""
    forecaster = get_forecaster()
    
    results = {}
    total_critical = 0
    total_warning = 0
    total_good = 0
    
    for district_id in forecaster.districts.keys():
        stock_status = forecaster.get_stock_status(district_id)
        
        critical_count = len([s for s in stock_status if s['status'] == 'critical'])
        warning_count = len([s for s in stock_status if s['status'] == 'warning'])
        good_count = len([s for s in stock_status if s['status'] == 'good'])
        
        total_critical += critical_count
        total_warning += warning_count
        total_good += good_count
        
        # Calculate overall district status
        if critical_count > 0:
            district_status = 'critical'
        elif warning_count > 0:
            district_status = 'warning'
        else:
            district_status = 'good'
        
        results[district_id] = {
            'district_name': forecaster.districts[district_id]['name'],
            'status': district_status,
            'critical_items': critical_count,
            'warning_items': warning_count,
            'good_items': good_count
        }
    
    # Calculate overall readiness
    total_items = total_critical + total_warning + total_good
    readiness = int((total_good / total_items) * 100) if total_items > 0 else 0
    
    return {
        'overall_readiness': readiness,
        'summary': {
            'critical_items': total_critical,
            'warning_items': total_warning,
            'good_items': total_good
        },
        'districts': results,
        'generated_at': datetime.now().isoformat()
    }


@router.get("/{district_id}")
async def get_district_stock(district_id: str):
    """Get detailed stock status for a district"""
    forecaster = get_forecaster()
    
    if district_id not in forecaster.districts:
        raise HTTPException(status_code=404, detail=f"District {district_id} not found")
    
    stock_status = forecaster.get_stock_status(district_id)
    
    # Sort by status (critical first)
    status_order = {'critical': 0, 'warning': 1, 'good': 2}
    stock_status.sort(key=lambda x: status_order[x['status']])
    
    return {
        'district_id': district_id,
        'district_name': forecaster.districts[district_id]['name'],
        'stock_items': stock_status,
        'summary': {
            'critical': len([s for s in stock_status if s['status'] == 'critical']),
            'warning': len([s for s in stock_status if s['status'] == 'warning']),
            'good': len([s for s in stock_status if s['status'] == 'good'])
        },
        'generated_at': datetime.now().isoformat()
    }


@router.get("/gaps/all")
async def get_all_stock_gaps():
    """Get all stock gaps across districts"""
    forecaster = get_forecaster()
    
    gaps = []
    
    for district_id in forecaster.districts.keys():
        stock_status = forecaster.get_stock_status(district_id)
        
        for stock in stock_status:
            if stock['stock_gap'] < 0:  # Deficit
                gaps.append({
                    'district_id': district_id,
                    'district_name': forecaster.districts[district_id]['name'],
                    'medicine_id': stock['medicine_id'],
                    'medicine_name': stock['medicine_name'],
                    'gap': abs(stock['stock_gap']),
                    'current_stock': stock['current_stock'],
                    'predicted_demand': stock['predicted_14d_demand'],
                    'days_until_stockout': stock['days_until_stockout'],
                    'status': stock['status']
                })
    
    # Sort by severity (days until stockout)
    gaps.sort(key=lambda x: x['days_until_stockout'])
    
    return {
        'total_gaps': len(gaps),
        'gaps': gaps,
        'generated_at': datetime.now().isoformat()
    }
