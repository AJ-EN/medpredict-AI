"use client";

import { useState, useEffect } from "react";
import {
    Bell,
    AlertTriangle,
    TrendingUp,
    CloudRain,
    Calendar,
    Activity,
    RefreshCw
} from "lucide-react";
import {
    getAlerts,
    getDistrictSignals,
    getRiskColor
} from "@/lib/api";

export default function AlertsPage() {
    const [alerts, setAlerts] = useState<any>(null);
    const [selectedDistrict, setSelectedDistrict] = useState<string | null>(null);
    const [signals, setSignals] = useState<any>(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        loadData();
    }, []);

    useEffect(() => {
        if (selectedDistrict) {
            loadSignals(selectedDistrict);
        }
    }, [selectedDistrict]);

    async function loadData() {
        setLoading(true);
        try {
            const data = await getAlerts();
            setAlerts(data);
            if (data.alerts?.[0]) {
                setSelectedDistrict(data.alerts[0].district_id);
            }
        } catch (error) {
            console.error("Error loading alerts:", error);
        }
        setLoading(false);
    }

    async function loadSignals(districtId: string) {
        try {
            const data = await getDistrictSignals(districtId);
            setSignals(data);
        } catch (error) {
            console.error("Error loading signals:", error);
        }
    }

    if (loading) {
        return (
            <div style={{ display: "flex", alignItems: "center", justifyContent: "center", minHeight: "50vh" }}>
                <RefreshCw className="animate-spin" size={32} />
            </div>
        );
    }

    return (
        <div>
            {/* Header */}
            <div style={{ marginBottom: 32 }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                    <div>
                        <h1 style={{ fontSize: 28, fontWeight: 700, marginBottom: 4 }}>
                            🚨 Early Warning Console
                        </h1>
                        <p style={{ color: "var(--muted)" }}>
                            Multi-signal outbreak detection and risk monitoring
                        </p>
                    </div>
                    <div style={{ display: "flex", gap: 12 }}>
                        <span className="badge badge-red">{alerts?.summary?.red || 0} Critical</span>
                        <span className="badge badge-orange">{alerts?.summary?.orange || 0} Elevated</span>
                        <span className="badge badge-yellow">{alerts?.summary?.yellow || 0} Watch</span>
                    </div>
                </div>
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "1fr 1.5fr", gap: 24 }}>
                {/* Alert List */}
                <div className="card">
                    <h2 style={{ fontSize: 16, fontWeight: 600, marginBottom: 16 }}>Active Alerts</h2>
                    <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                        {alerts?.alerts?.map((alert: any) => (
                            <div
                                key={alert.id}
                                onClick={() => setSelectedDistrict(alert.district_id)}
                                style={{
                                    padding: 16,
                                    borderRadius: 8,
                                    background: selectedDistrict === alert.district_id ? 'rgba(59,130,246,0.1)' : 'var(--card)',
                                    border: `1px solid ${selectedDistrict === alert.district_id ? 'var(--accent)' : 'var(--border)'}`,
                                    cursor: "pointer",
                                    transition: "all 0.2s ease"
                                }}
                            >
                                <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 8 }}>
                                    <div style={{
                                        width: 10,
                                        height: 10,
                                        borderRadius: "50%",
                                        background: getRiskColor(alert.level),
                                        boxShadow: `0 0 8px ${getRiskColor(alert.level)}`
                                    }} />
                                    <span style={{ fontWeight: 600 }}>{alert.district_name}</span>
                                    <span className={`badge badge-${alert.level}`} style={{ marginLeft: "auto" }}>
                                        {alert.level}
                                    </span>
                                </div>
                                <div style={{ fontSize: 13, color: "var(--muted)" }}>
                                    {alert.message}
                                </div>
                            </div>
                        ))}

                        {(!alerts?.alerts || alerts.alerts.length === 0) && (
                            <div style={{ textAlign: "center", padding: 60, color: "var(--muted)" }}>
                                <Bell size={40} style={{ opacity: 0.3, marginBottom: 16 }} />
                                <div>No active alerts</div>
                                <div style={{ fontSize: 13, marginTop: 4 }}>All districts within normal parameters</div>
                            </div>
                        )}
                    </div>
                </div>

                {/* Signal Analysis */}
                <div className="card">
                    <h2 style={{ fontSize: 16, fontWeight: 600, marginBottom: 16 }}>
                        📊 Signal Analysis: {signals?.district_name || "Select a district"}
                    </h2>

                    {signals && (
                        <div>
                            {/* Overall Risk */}
                            <div style={{
                                padding: 20,
                                background: `${getRiskColor(signals.overall_risk?.level)}15`,
                                borderRadius: 12,
                                border: `1px solid ${getRiskColor(signals.overall_risk?.level)}30`,
                                marginBottom: 24,
                                textAlign: "center"
                            }}>
                                <div style={{ fontSize: 14, color: "var(--muted)", marginBottom: 8 }}>Combined Risk Score</div>
                                <div style={{
                                    fontSize: 48,
                                    fontWeight: 700,
                                    color: getRiskColor(signals.overall_risk?.level)
                                }}>
                                    {((signals.overall_risk?.score || 0) * 100).toFixed(0)}%
                                </div>
                                <div style={{ marginTop: 8 }}>
                                    <span className={`badge badge-${signals.overall_risk?.level}`}>
                                        {signals.overall_risk?.level?.toUpperCase()} RISK
                                    </span>
                                </div>
                            </div>

                            {/* Signal Bars */}
                            <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
                                <SignalBar
                                    icon={<CloudRain size={18} />}
                                    label="Weather Signal"
                                    value={signals.signals?.weather?.value || 0}
                                    description={signals.signals?.weather?.description}
                                />
                                <SignalBar
                                    icon={<Calendar size={18} />}
                                    label="Seasonal Pattern"
                                    value={signals.signals?.seasonal?.value || 0}
                                    description={signals.signals?.seasonal?.description}
                                />
                                <SignalBar
                                    icon={<TrendingUp size={18} />}
                                    label="Case Trend"
                                    value={signals.signals?.trend?.value || 0}
                                    description={signals.signals?.trend?.description}
                                />
                            </div>

                            {/* Weather Data */}
                            {signals.signals?.weather?.data && (
                                <div style={{ marginTop: 24, padding: 16, background: "var(--card)", borderRadius: 8 }}>
                                    <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 12 }}>Current Conditions</div>
                                    <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 12 }}>
                                        <div>
                                            <div style={{ fontSize: 12, color: "var(--muted)" }}>Temperature</div>
                                            <div style={{ fontWeight: 600 }}>{signals.signals.weather.data.temperature?.toFixed(1)}°C</div>
                                        </div>
                                        <div>
                                            <div style={{ fontSize: 12, color: "var(--muted)" }}>Rainfall (14d)</div>
                                            <div style={{ fontWeight: 600 }}>{signals.signals.weather.data.rainfall_14d?.toFixed(0)}mm</div>
                                        </div>
                                        <div>
                                            <div style={{ fontSize: 12, color: "var(--muted)" }}>Humidity</div>
                                            <div style={{ fontWeight: 600 }}>{signals.signals.weather.data.humidity?.toFixed(0)}%</div>
                                        </div>
                                    </div>
                                </div>
                            )}
                        </div>
                    )}

                    {!signals && (
                        <div style={{ textAlign: "center", padding: 60, color: "var(--muted)" }}>
                            <Activity size={40} style={{ opacity: 0.3, marginBottom: 16 }} />
                            <div>Select a district to view signal analysis</div>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}

function SignalBar({
    icon,
    label,
    value,
    description
}: {
    icon: React.ReactNode;
    label: string;
    value: number;
    description?: string;
}) {
    const percentage = (value * 100).toFixed(0);

    return (
        <div>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
                <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                    {icon}
                    <span style={{ fontWeight: 500 }}>{label}</span>
                </div>
                <span style={{ fontWeight: 600 }}>{percentage}%</span>
            </div>
            <div className="signal-bar">
                <div
                    className="signal-fill"
                    style={{
                        width: `${percentage}%`,
                        background: value > 0.7 ? 'linear-gradient(90deg, #ef4444 0%, #dc2626 100%)' :
                            value > 0.5 ? 'linear-gradient(90deg, #f59e0b 0%, #d97706 100%)' :
                                'linear-gradient(90deg, #3b82f6 0%, #2563eb 100%)'
                    }}
                />
            </div>
            {description && (
                <div style={{ fontSize: 12, color: "var(--muted)", marginTop: 6 }}>
                    {description}
                </div>
            )}
        </div>
    );
}
