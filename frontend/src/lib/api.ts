const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export interface District {
    id: string;
    name: string;
    population: number;
    type: string;
    lat: number;
    lng: number;
}

export interface RiskScore {
    score: number;
    level: 'red' | 'orange' | 'yellow' | 'green';
    signals: {
        weather: number;
        seasonal: number;
        trend: number;
    };
    weather_data: {
        temperature: number;
        rainfall: number;
        humidity: number;
        rainfall_14d: number;
        condition?: string;
        is_real_data?: boolean;
    };
}

export interface Forecast {
    date: string;
    predicted: number;
    lower_bound: number;
    upper_bound: number;
    confidence: number;
}

export interface Alert {
    id: string;
    district_id: string;
    district_name: string;
    level: 'red' | 'orange' | 'yellow';
    risk_score: number;
    title: string;
    message: string;
    signals: Record<string, number>;
    recommended_actions: string[];
    triggered_at: string;
}

export interface StockItem {
    medicine_id: string;
    medicine_name: string;
    current_stock: number;
    safety_stock: number;
    predicted_14d_demand: number;
    stock_gap: number;
    days_until_stockout: number;
    stock_percentage: number;
    status: 'critical' | 'warning' | 'good';
}

export interface Recommendation {
    priority: 'urgent' | 'high' | 'medium';
    type: string;
    medicine_id?: string;
    medicine_name?: string;
    action: string;
    reason: string;
    deadline: string;
}

// API Functions
export async function getConfig() {
    const res = await fetch(`${API_BASE}/api/config`);
    return res.json();
}

export async function getStateForecast(daysAhead: number = 14) {
    const res = await fetch(`${API_BASE}/api/forecast/state?days_ahead=${daysAhead}`);
    return res.json();
}

export async function getDistrictForecast(districtId: string, disease: string = 'dengue', daysAhead: number = 14) {
    const res = await fetch(`${API_BASE}/api/forecast/${districtId}?disease=${disease}&days_ahead=${daysAhead}`);
    return res.json();
}

export async function getAllMedicineForecast(districtId: string, daysAhead: number = 14) {
    const res = await fetch(`${API_BASE}/api/forecast/${districtId}/all-medicines?days_ahead=${daysAhead}`);
    return res.json();
}

export async function getAlerts(level?: string) {
    const url = level ? `${API_BASE}/api/alerts?level=${level}` : `${API_BASE}/api/alerts`;
    const res = await fetch(url);
    return res.json();
}

export async function getDistrictSignals(districtId: string) {
    const res = await fetch(`${API_BASE}/api/alerts/signals/${districtId}`);
    return res.json();
}

export async function getAlertTimeline(districtId: string) {
    const res = await fetch(`${API_BASE}/api/alerts/timeline/${districtId}`);
    return res.json();
}

export async function getStateStock() {
    const res = await fetch(`${API_BASE}/api/stock/state`);
    return res.json();
}

export async function getDistrictStock(districtId: string) {
    const res = await fetch(`${API_BASE}/api/stock/${districtId}`);
    return res.json();
}

export async function getRecommendations(districtId: string) {
    const res = await fetch(`${API_BASE}/api/recommendations/${districtId}`);
    return res.json();
}

export async function simulateScenario(severityMultiplier: number, responseDays: number) {
    const res = await fetch(
        `${API_BASE}/api/recommendations/simulate?severity_multiplier=${severityMultiplier}&response_days=${responseDays}`,
        { method: 'POST' }
    );
    return res.json();
}

// Helper function for risk level colors
export function getRiskColor(level: string): string {
    switch (level) {
        case 'red': return '#ef4444';
        case 'orange': return '#f59e0b';
        case 'yellow': return '#eab308';
        case 'green': return '#22c55e';
        default: return '#71717a';
    }
}

export function getRiskEmoji(level: string): string {
    switch (level) {
        case 'red': return '🔴';
        case 'orange': return '🟠';
        case 'yellow': return '🟡';
        case 'green': return '🟢';
        default: return '⚪';
    }
}
