"use client";

import { useState, useEffect } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import {
    ArrowLeft,
    TrendingUp,
    Package,
    AlertTriangle,
    Thermometer,
    CloudRain,
    Droplets,
    RefreshCw
} from "lucide-react";
import {
    LineChart,
    Line,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    ResponsiveContainer,
    Area,
    AreaChart
} from "recharts";
import {
    getDistrictForecast,
    getDistrictStock,
    getRecommendations,
    getDistrictSignals,
    getRiskColor,
    getRiskEmoji
} from "@/lib/api";

export default function DistrictPage() {
    const params = useParams();
    const districtId = params.id as string;

    const [forecast, setForecast] = useState<any>(null);
    const [stock, setStock] = useState<any>(null);
    const [recommendations, setRecommendations] = useState<any>(null);
    const [signals, setSignals] = useState<any>(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        loadData();
    }, [districtId]);

    async function loadData() {
        setLoading(true);
        try {
            const [fc, st, rec, sig] = await Promise.all([
                getDistrictForecast(districtId, 'dengue', 14),
                getDistrictStock(districtId),
                getRecommendations(districtId),
                getDistrictSignals(districtId)
            ]);
            setForecast(fc);
            setStock(st);
            setRecommendations(rec);
            setSignals(sig);
        } catch (error) {
            console.error("Error loading data:", error);
        }
        setLoading(false);
    }

    if (loading) {
        return (
            <div style={{ display: "flex", alignItems: "center", justifyContent: "center", minHeight: "50vh" }}>
                <RefreshCw className="animate-spin" size={32} />
            </div>
        );
    }

    const riskLevel = forecast?.risk?.level || 'green';
    const riskScore = forecast?.risk?.score || 0;

    return (
        <div>
            {/* Header */}
            <div style={{ marginBottom: 32 }}>
                <Link href="/" style={{
                    display: "inline-flex",
                    alignItems: "center",
                    gap: 8,
                    color: "var(--muted)",
                    textDecoration: "none",
                    marginBottom: 16
                }}>
                    <ArrowLeft size={16} />
                    Back to Overview
                </Link>

                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                    <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
                        <h1 style={{ fontSize: 28, fontWeight: 700 }}>
                            {forecast?.district_name || districtId}
                        </h1>
                        <span className={`badge badge-${riskLevel}`} style={{ fontSize: 14 }}>
                            {getRiskEmoji(riskLevel)} Risk: {riskLevel.toUpperCase()}
                        </span>
                    </div>
                    <button onClick={loadData} className="btn btn-ghost">
                        <RefreshCw size={16} />
                        Refresh
                    </button>
                </div>
            </div>

            {/* Risk Signal Cards */}
            <div className="bento-grid bento-grid-4" style={{ marginBottom: 24 }}>
                <div className="card">
                    <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 12 }}>
                        <Thermometer size={18} color="var(--warning)" />
                        <span style={{ color: "var(--muted)", fontSize: 13 }}>Temperature</span>
                    </div>
                    <div style={{ fontSize: 24, fontWeight: 700 }}>
                        {signals?.signals?.weather?.data?.temperature?.toFixed(1) || '--'}°C
                    </div>
                </div>
                <div className="card">
                    <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 12 }}>
                        <CloudRain size={18} color="var(--accent)" />
                        <span style={{ color: "var(--muted)", fontSize: 13 }}>Rainfall (14d)</span>
                    </div>
                    <div style={{ fontSize: 24, fontWeight: 700 }}>
                        {signals?.signals?.weather?.data?.rainfall_14d?.toFixed(0) || '--'}mm
                    </div>
                </div>
                <div className="card">
                    <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 12 }}>
                        <Droplets size={18} color="var(--success)" />
                        <span style={{ color: "var(--muted)", fontSize: 13 }}>Humidity</span>
                    </div>
                    <div style={{ fontSize: 24, fontWeight: 700 }}>
                        {signals?.signals?.weather?.data?.humidity?.toFixed(0) || '--'}%
                    </div>
                </div>
                <div className="card">
                    <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 12 }}>
                        <TrendingUp size={18} color={getRiskColor(riskLevel)} />
                        <span style={{ color: "var(--muted)", fontSize: 13 }}>Risk Score</span>
                    </div>
                    <div style={{ fontSize: 24, fontWeight: 700, color: getRiskColor(riskLevel) }}>
                        {(riskScore * 100).toFixed(0)}%
                    </div>
                </div>
            </div>

            {/* Forecast Chart */}
            <div className="card" style={{ marginBottom: 24 }}>
                <h2 style={{ fontSize: 18, fontWeight: 600, marginBottom: 20 }}>
                    📈 Dengue Case Forecast (14 Days)
                </h2>
                <div style={{ height: 300 }}>
                    <ResponsiveContainer width="100%" height="100%">
                        <AreaChart data={forecast?.forecast || []}>
                            <defs>
                                <linearGradient id="colorPredicted" x1="0" y1="0" x2="0" y2="1">
                                    <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3} />
                                    <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
                                </linearGradient>
                            </defs>
                            <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                            <XAxis
                                dataKey="date"
                                tick={{ fill: 'var(--muted)', fontSize: 12 }}
                                tickFormatter={(val) => new Date(val).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
                            />
                            <YAxis tick={{ fill: 'var(--muted)', fontSize: 12 }} />
                            <Tooltip
                                contentStyle={{
                                    background: 'var(--card)',
                                    border: '1px solid var(--border)',
                                    borderRadius: 8
                                }}
                                labelFormatter={(val) => new Date(val).toLocaleDateString()}
                            />
                            <Area
                                type="monotone"
                                dataKey="upper_bound"
                                stroke="transparent"
                                fill="#3b82f6"
                                fillOpacity={0.1}
                            />
                            <Area
                                type="monotone"
                                dataKey="lower_bound"
                                stroke="transparent"
                                fill="#0a0a0f"
                            />
                            <Line
                                type="monotone"
                                dataKey="predicted"
                                stroke="#3b82f6"
                                strokeWidth={3}
                                dot={false}
                            />
                        </AreaChart>
                    </ResponsiveContainer>
                </div>
                <div style={{ display: "flex", gap: 24, marginTop: 16, justifyContent: "center" }}>
                    <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                        <div style={{ width: 24, height: 3, background: "#3b82f6", borderRadius: 2 }} />
                        <span style={{ fontSize: 12, color: "var(--muted)" }}>Predicted Cases</span>
                    </div>
                    <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                        <div style={{ width: 24, height: 12, background: "rgba(59,130,246,0.2)", borderRadius: 2 }} />
                        <span style={{ fontSize: 12, color: "var(--muted)" }}>95% Confidence Interval</span>
                    </div>
                </div>
            </div>

            <div className="bento-grid bento-grid-2">
                {/* Stock Status */}
                <div className="card">
                    <h2 style={{ fontSize: 18, fontWeight: 600, marginBottom: 20 }}>
                        📦 Stock Status
                    </h2>
                    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
                        {stock?.stock_items?.map((item: any) => (
                            <div key={item.medicine_id}>
                                <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 8 }}>
                                    <span style={{ fontWeight: 500 }}>{item.medicine_name}</span>
                                    <span style={{
                                        color: item.status === 'critical' ? 'var(--danger)' :
                                            item.status === 'warning' ? 'var(--warning)' : 'var(--success)'
                                    }}>
                                        {item.stock_percentage}%
                                    </span>
                                </div>
                                <div className="progress-bar">
                                    <div
                                        className={`progress-fill progress-${item.status === 'critical' ? 'critical' : item.status === 'warning' ? 'warning' : 'good'}`}
                                        style={{ width: `${Math.min(item.stock_percentage, 100)}%` }}
                                    />
                                </div>
                                <div style={{ fontSize: 12, color: "var(--muted)", marginTop: 4 }}>
                                    {item.current_stock.toLocaleString()} units • {item.days_until_stockout} days until stockout
                                </div>
                            </div>
                        ))}
                    </div>
                </div>

                {/* Recommendations */}
                <div className="card">
                    <h2 style={{ fontSize: 18, fontWeight: 600, marginBottom: 20 }}>
                        📋 Recommended Actions
                    </h2>
                    <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
                        {recommendations?.recommendations?.map((rec: any, i: number) => (
                            <div
                                key={i}
                                style={{
                                    padding: 16,
                                    borderRadius: 8,
                                    background: rec.priority === 'urgent' ? 'var(--danger-bg)' :
                                        rec.priority === 'high' ? 'var(--warning-bg)' : 'var(--card)',
                                    border: `1px solid ${rec.priority === 'urgent' ? 'rgba(239,68,68,0.3)' :
                                        rec.priority === 'high' ? 'rgba(245,158,11,0.3)' : 'var(--border)'}`
                                }}
                            >
                                <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 8 }}>
                                    {rec.priority === 'urgent' && <AlertTriangle size={16} color="var(--danger)" />}
                                    <span style={{
                                        fontSize: 11,
                                        textTransform: "uppercase",
                                        fontWeight: 600,
                                        color: rec.priority === 'urgent' ? 'var(--danger)' : 'var(--warning)'
                                    }}>
                                        {rec.priority}
                                    </span>
                                </div>
                                <div style={{ fontWeight: 500, marginBottom: 4 }}>{rec.action}</div>
                                <div style={{ fontSize: 13, color: "var(--muted)" }}>{rec.reason}</div>
                                <div style={{ fontSize: 12, color: "var(--muted)", marginTop: 8 }}>
                                    Deadline: {new Date(rec.deadline).toLocaleDateString()}
                                </div>
                            </div>
                        ))}

                        {(!recommendations?.recommendations || recommendations.recommendations.length === 0) && (
                            <div style={{ textAlign: "center", padding: 40, color: "var(--muted)" }}>
                                No urgent recommendations
                            </div>
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
}
