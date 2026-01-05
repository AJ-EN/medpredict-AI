"""
Alerts API Router
"""

from fastapi import APIRouter, Query
from typing import List, Optional
from datetime import datetime

router = APIRouter()


def get_forecaster():
    from app.main import forecaster
    return forecaster


@router.get("/")
async def get_all_alerts(level: Optional[str] = Query(None)):
    """Get all active alerts across districts"""
    forecaster = get_forecaster()
    
    alerts = []
    for district_id, district in forecaster.districts.items():
        risk = forecaster.calculate_risk_score(district_id)
        anomalies = forecaster.detect_anomalies(district_id)
        
        if level and risk['level'] != level:
            continue
        
        if risk['level'] in ['red', 'orange', 'yellow']:
            alert = {
                'id': f"alert-{district_id}-{datetime.now().strftime('%Y%m%d')}",
                'district_id': district_id,
                'district_name': district['name'],
                'level': risk['level'],
                'risk_score': risk['score'],
                'title': _get_alert_title(risk['level'], district['name']),
                'message': _get_alert_message(risk, anomalies),
                'signals': risk['signals'],
                'anomalies': anomalies,
                'triggered_at': datetime.now().isoformat(),
                'recommended_actions': _get_recommended_actions(risk['level'])
            }
            alerts.append(alert)
    
    # Sort by severity
    severity_order = {'red': 0, 'orange': 1, 'yellow': 2, 'green': 3}
    alerts.sort(key=lambda x: severity_order[x['level']])
    
    return {
        'count': len(alerts),
        'summary': {
            'red': len([a for a in alerts if a['level'] == 'red']),
            'orange': len([a for a in alerts if a['level'] == 'orange']),
            'yellow': len([a for a in alerts if a['level'] == 'yellow'])
        },
        'alerts': alerts
    }


@router.get("/signals/{district_id}")
async def get_district_signals(district_id: str):
    """Get detailed signal breakdown for a district"""
    forecaster = get_forecaster()
    
    risk = forecaster.calculate_risk_score(district_id)
    weather = forecaster.get_current_weather(district_id)
    anomalies = forecaster.detect_anomalies(district_id)
    
    return {
        'district_id': district_id,
        'district_name': forecaster.districts[district_id]['name'],
        'overall_risk': {
            'score': risk['score'],
            'level': risk['level']
        },
        'signals': {
            'weather': {
                'value': risk['signals'].get('causal_weather', risk['signals'].get('weather', 0)),
                'description': _describe_weather_signal(weather),
                'data': weather
            },
            'seasonal': {
                'value': risk['signals']['seasonal'],
                'description': _describe_seasonal_signal(risk['signals']['seasonal'])
            },
            'trend': {
                'value': risk['signals']['trend'],
                'description': _describe_trend_signal(risk['signals']['trend'])
            }
        },
        'anomalies': anomalies,
        'generated_at': datetime.now().isoformat()
    }


@router.get("/timeline/{district_id}")
async def get_alert_timeline(district_id: str, days: int = Query(7, ge=1, le=30)):
    """Get historical alert timeline for a district (simulated)"""
    forecaster = get_forecaster()
    
    # Generate simulated timeline
    timeline = []
    base_date = datetime.now()
    
    risk = forecaster.calculate_risk_score(district_id)
    
    # Create timeline entries based on current signals
    weather_signal = risk['signals'].get('causal_weather', risk['signals'].get('weather', 0))
    if weather_signal > 0.6:
        timeline.append({
            'date': base_date.strftime('%Y-%m-%d'),
            'event': 'weather_signal',
            'level': 'orange' if weather_signal > 0.7 else 'yellow',
            'message': f"Weather conditions from 14 days ago indicate elevated risk"
        })
    
    if risk['signals']['trend'] > 0.6:
        timeline.append({
            'date': base_date.strftime('%Y-%m-%d'),
            'event': 'trend_signal',
            'level': 'yellow',
            'message': 'Case trend showing uptick'
        })
    
    if risk['level'] in ['red', 'orange']:
        timeline.append({
            'date': base_date.strftime('%Y-%m-%d'),
            'event': 'combined_alert',
            'level': risk['level'],
            'message': f"Combined risk crossed {0.75 if risk['level'] == 'red' else 0.5} threshold"
        })
    
    return {
        'district_id': district_id,
        'timeline': timeline
    }


def _get_alert_title(level: str, district_name: str) -> str:
    if level == 'red':
        return f"🔴 HIGH RISK: {district_name}"
    elif level == 'orange':
        return f"🟠 ELEVATED: {district_name}"
    else:
        return f"🟡 WATCH: {district_name}"


def _get_alert_message(risk: dict, anomalies: list) -> str:
    parts = []
    
    weather_signal = risk['signals'].get('causal_weather', risk['signals'].get('weather', 0))
    if weather_signal > 0.7:
        parts.append(f"Causal weather signal (14-day lag) indicates high transmission risk")
    
    if risk['signals'].get('trend', 0) > 0.6:
        parts.append(f"Case trend showing increase")
    
    for anomaly in anomalies:
        parts.append(anomaly['message'])
    
    return ". ".join(parts) if parts else "Elevated risk detected based on multiple signals"


def _get_recommended_actions(level: str) -> List[str]:
    if level == 'red':
        return [
            "Verify stock levels for key medicines",
            "Alert district hospital for surge preparation",
            "Consider requesting emergency stock transfer",
            "Increase surveillance reporting frequency"
        ]
    elif level == 'orange':
        return [
            "Review stock levels for key medicines",
            "Prepare redistribution plan",
            "Monitor situation closely"
        ]
    else:
        return [
            "Continue routine monitoring",
            "Ensure stock levels are maintained"
        ]


def _describe_weather_signal(weather: dict) -> str:
    rainfall = weather.get('rainfall_lag_14d', weather.get('rainfall_14d', 0))
    breeding_index = weather.get('breeding_index_lag', 0)
    
    if breeding_index > 1.0:
        return f"High mosquito breeding conditions (index: {breeding_index:.2f})"
    elif rainfall > 50:
        return f"Moderate rainfall ({rainfall:.0f}mm) with favorable temperature"
    else:
        return f"Low rainfall, limited mosquito breeding"


def _describe_seasonal_signal(value: float) -> str:
    if value > 0.7:
        return "Peak monsoon season - historically high risk period"
    elif value > 0.4:
        return "Pre/post monsoon - moderate seasonal risk"
    else:
        return "Low season for vector-borne diseases"


def _describe_trend_signal(value: float) -> str:
    if value > 0.7:
        return "Cases trending upward significantly"
    elif value > 0.5:
        return "Slight upward trend in cases"
    else:
        return "Stable or declining case trend"
