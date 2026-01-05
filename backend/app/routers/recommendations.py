"""
Recommendations API Router
With Network Optimization and Causal Context
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from datetime import datetime

router = APIRouter()


@router.get("/network")
async def get_network_optimization():
    """
    FIRST PRINCIPLES: Optimize the entire network, not individual districts
    Returns transfers and orders that minimize total system cost
    """
    forecaster = get_forecaster()
    
    plan = forecaster.optimize_network_transfers()
    
    total_transfer_savings = sum(t.get('cost_saved', 0) for t in plan['transfers'])
    
    return {
        'network_plan': plan,
        'summary': {
            'total_transfers': len(plan['transfers']),
            'total_orders': len(plan['orders']),
            'estimated_savings': total_transfer_savings
        },
        'note': 'Transfers are prioritized over procurement to use existing surplus',
        'generated_at': datetime.now().isoformat()
    }


def get_forecaster():
    from app.main import forecaster
    return forecaster


@router.get("/{district_id}")
async def get_recommendations(district_id: str):
    """Get actionable recommendations for a district"""
    forecaster = get_forecaster()
    
    if district_id not in forecaster.districts:
        raise HTTPException(status_code=404, detail=f"District {district_id} not found")
    
    recommendations = forecaster.get_recommendations(district_id)
    
    return {
        'district_id': district_id,
        'district_name': forecaster.districts[district_id]['name'],
        'recommendations': recommendations,
        'count': len(recommendations),
        'urgent_count': len([r for r in recommendations if r['priority'] == 'urgent']),
        'generated_at': datetime.now().isoformat()
    }


@router.post("/simulate")
async def simulate_scenario(
    severity_multiplier: float = Query(1.0, ge=0.5, le=10.0),
    response_days: int = Query(7, ge=0, le=21)
):
    """
    Simulate outbreak scenario and calculate impact
    """
    forecaster = get_forecaster()
    
    # Calculate baseline metrics
    total_stockouts_without = 0
    total_stockouts_with = 0
    
    for district_id in forecaster.districts.keys():
        stock_status = forecaster.get_stock_status(district_id)
        
        for stock in stock_status:
            # Simulated demand with severity multiplier
            adjusted_demand = stock['predicted_14d_demand'] * severity_multiplier
            
            # Without system: 14 day response
            days_to_respond_without = 14
            demand_before_response = adjusted_demand * (days_to_respond_without / 14)
            if stock['current_stock'] < demand_before_response:
                total_stockouts_without += 1
            
            # With system: early response
            demand_before_response_with = adjusted_demand * (response_days / 14)
            # Plus can pre-position stock
            effective_stock = stock['current_stock'] * 1.3  # Buffer from early warning
            if effective_stock < demand_before_response_with:
                total_stockouts_with += 1
    
    stockouts_prevented = total_stockouts_without - total_stockouts_with
    
    # Estimate lives impacted (rough estimate)
    lives_impacted = int(stockouts_prevented * 2)  # ~2 per stockout event
    
    # Cost comparison
    emergency_cost = total_stockouts_without * 50000  # ₹50k per emergency
    planned_cost = total_stockouts_with * 15000  # ₹15k with planning
    savings = emergency_cost - planned_cost
    
    return {
        'scenario': {
            'severity_multiplier': severity_multiplier,
            'response_days': response_days
        },
        'results': {
            'without_system': {
                'stockout_events': total_stockouts_without,
                'response_time_days': 14,
                'estimated_cost': emergency_cost
            },
            'with_system': {
                'stockout_events': total_stockouts_with,
                'response_time_days': response_days,
                'estimated_cost': planned_cost
            },
            'impact': {
                'stockouts_prevented': stockouts_prevented,
                'response_time_saved_days': 14 - response_days,
                'estimated_lives_impacted': lives_impacted,
                'cost_savings': savings
            }
        },
        'generated_at': datetime.now().isoformat()
    }


@router.get("/transfers/suggested")
async def get_suggested_transfers():
    """Get suggested inter-district transfers"""
    forecaster = get_forecaster()
    
    transfers = []
    
    # Find surplus and deficit districts
    district_status = {}
    for district_id in forecaster.districts.keys():
        stock_status = forecaster.get_stock_status(district_id)
        risk = forecaster.calculate_risk_score(district_id)
        
        district_status[district_id] = {
            'name': forecaster.districts[district_id]['name'],
            'risk_level': risk['level'],
            'stocks': {s['medicine_id']: s for s in stock_status}
        }
    
    # Match deficits with surpluses
    for med_id in forecaster.medicines.keys():
        deficits = []
        surpluses = []
        
        for dist_id, status in district_status.items():
            stock = status['stocks'].get(med_id, {})
            if stock.get('status') == 'critical':
                deficits.append((dist_id, status['name'], stock.get('stock_gap', 0)))
            elif stock.get('stock_percentage', 0) > 100:
                surplus = stock.get('current_stock', 0) - stock.get('predicted_14d_demand', 0)
                if surplus > 0:
                    surpluses.append((dist_id, status['name'], surplus))
        
        # Create transfer recommendations
        for deficit in deficits:
            for surplus in surpluses:
                if abs(deficit[2]) <= surplus[2]:
                    transfers.append({
                        'medicine_id': med_id,
                        'medicine_name': forecaster.medicines[med_id]['name'],
                        'from_district': surplus[1],
                        'to_district': deficit[1],
                        'quantity': int(min(abs(deficit[2]), surplus[2])),
                        'priority': 'urgent'
                    })
                    break
    
    return {
        'suggested_transfers': transfers[:10],  # Top 10
        'generated_at': datetime.now().isoformat()
    }
