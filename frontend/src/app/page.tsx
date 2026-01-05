"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import {
  AlertTriangle,
  TrendingUp,
  Package,
  Activity,
  ChevronRight,
  RefreshCw
} from "lucide-react";
import {
  getStateForecast,
  getAlerts,
  getStateStock,
  getRiskColor,
  getRiskEmoji
} from "@/lib/api";

interface DistrictData {
  district_name: string;
  risk_level: string;
  risk_score: number;
  total_predicted_cases: number;
  peak_day: string;
}

export default function HomePage() {
  const [stateData, setStateData] = useState<Record<string, DistrictData> | null>(null);
  const [alerts, setAlerts] = useState<any>(null);
  const [stockData, setStockData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [lastUpdate, setLastUpdate] = useState<Date>(new Date());

  useEffect(() => {
    loadData();
  }, []);

  async function loadData() {
    setLoading(true);
    try {
      const [forecast, alertsRes, stock] = await Promise.all([
        getStateForecast(14),
        getAlerts(),
        getStateStock()
      ]);
      setStateData(forecast.districts);
      setAlerts(alertsRes);
      setStockData(stock);
      setLastUpdate(new Date());
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

  // Calculate summary stats
  const districts = stateData ? Object.entries(stateData) : [];
  const redCount = districts.filter(([_, d]) => d.risk_level === "red").length;
  const orangeCount = districts.filter(([_, d]) => d.risk_level === "orange").length;
  const totalCases = districts.reduce((sum, [_, d]) => sum + d.total_predicted_cases, 0);

  return (
    <div>
      {/* Header */}
      <div style={{ marginBottom: 32 }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <div>
            <h1 style={{ fontSize: 28, fontWeight: 700, marginBottom: 4 }}>State Overview</h1>
            <p style={{ color: "var(--muted)" }}>Rajasthan Medicine Demand Forecasting Dashboard</p>
          </div>
          <button onClick={loadData} className="btn btn-ghost">
            <RefreshCw size={16} />
            Refresh
          </button>
        </div>
      </div>

      {/* Stats Grid */}
      <div className="bento-grid bento-grid-4" style={{ marginBottom: 32 }}>
        <StatCard
          icon={<AlertTriangle color="#ef4444" />}
          label="High Risk Districts"
          value={redCount + orangeCount}
          subtext={`${redCount} critical, ${orangeCount} elevated`}
          trend={redCount > 0 ? "critical" : "normal"}
        />
        <StatCard
          icon={<TrendingUp color="#3b82f6" />}
          label="14-Day Case Forecast"
          value={totalCases.toLocaleString()}
          subtext="across all districts"
        />
        <StatCard
          icon={<Package color="#22c55e" />}
          label="Stock Readiness"
          value={`${stockData?.overall_readiness || 0}%`}
          subtext={`${stockData?.summary?.critical_items || 0} critical items`}
          trend={stockData?.overall_readiness > 70 ? "good" : "warning"}
        />
        <StatCard
          icon={<Activity color="#8b5cf6" />}
          label="Active Alerts"
          value={alerts?.count || 0}
          subtext={`${alerts?.summary?.red || 0} 🔴  ${alerts?.summary?.orange || 0} 🟠`}
        />
      </div>

      {/* Main Grid */}
      <div className="bento-grid bento-grid-2">
        {/* District Risk Map */}
        <div className="card" style={{ gridColumn: "span 1" }}>
          <h2 style={{ fontSize: 18, fontWeight: 600, marginBottom: 20 }}>District Risk Levels</h2>
          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            {districts
              .sort((a, b) => {
                const order: Record<string, number> = { red: 0, orange: 1, yellow: 2, green: 3 };
                return order[a[1].risk_level] - order[b[1].risk_level];
              })
              .map(([id, district]) => (
                <Link
                  href={`/district/${id}`}
                  key={id}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                    padding: "12px 16px",
                    background: "var(--card)",
                    borderRadius: 8,
                    textDecoration: "none",
                    color: "inherit",
                    transition: "all 0.2s ease"
                  }}
                >
                  <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
                    <span style={{ fontSize: 20 }}>{getRiskEmoji(district.risk_level)}</span>
                    <div>
                      <div style={{ fontWeight: 500 }}>{district.district_name}</div>
                      <div style={{ fontSize: 12, color: "var(--muted)" }}>
                        {district.total_predicted_cases} cases predicted
                      </div>
                    </div>
                  </div>
                  <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
                    <span
                      className={`badge badge-${district.risk_level}`}
                    >
                      {district.risk_level}
                    </span>
                    <ChevronRight size={16} color="var(--muted)" />
                  </div>
                </Link>
              ))}
          </div>
        </div>

        {/* Alerts Panel */}
        <div className="card">
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 20 }}>
            <h2 style={{ fontSize: 18, fontWeight: 600 }}>Active Alerts</h2>
            <Link href="/alerts" style={{ color: "var(--accent)", fontSize: 14, textDecoration: "none" }}>
              View All →
            </Link>
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
            {alerts?.alerts?.slice(0, 5).map((alert: any) => (
              <div
                key={alert.id}
                className={`alert-card alert-card-${alert.level}`}
              >
                <div style={{
                  width: 40,
                  height: 40,
                  borderRadius: 8,
                  background: getRiskColor(alert.level),
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  flexShrink: 0
                }}>
                  <AlertTriangle size={20} color="white" />
                </div>
                <div style={{ flex: 1 }}>
                  <div style={{ fontWeight: 600, marginBottom: 4 }}>{alert.title}</div>
                  <div style={{ fontSize: 13, color: "var(--muted)", lineHeight: 1.4 }}>
                    {alert.message}
                  </div>
                </div>
              </div>
            ))}

            {(!alerts?.alerts || alerts.alerts.length === 0) && (
              <div style={{ textAlign: "center", padding: 40, color: "var(--muted)" }}>
                No active alerts
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Footer */}
      <div style={{ marginTop: 32, textAlign: "center", color: "var(--muted)", fontSize: 12 }}>
        Last updated: {lastUpdate.toLocaleString()} • Powered by MedPredict AI
      </div>
    </div>
  );
}

function StatCard({
  icon,
  label,
  value,
  subtext,
  trend
}: {
  icon: React.ReactNode;
  label: string;
  value: string | number;
  subtext: string;
  trend?: string;
}) {
  return (
    <div className="card">
      <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 16 }}>
        <div style={{
          width: 40,
          height: 40,
          borderRadius: 10,
          background: "rgba(255,255,255,0.05)",
          display: "flex",
          alignItems: "center",
          justifyContent: "center"
        }}>
          {icon}
        </div>
        <span style={{ color: "var(--muted)", fontSize: 14 }}>{label}</span>
      </div>
      <div className="stat-value">{value}</div>
      <div style={{
        marginTop: 8,
        fontSize: 13,
        color: trend === "critical" ? "var(--danger)" : trend === "good" ? "var(--success)" : "var(--muted)"
      }}>
        {subtext}
      </div>
    </div>
  );
}
