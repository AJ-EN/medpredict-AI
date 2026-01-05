"use client";

import { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import {
  AlertTriangle,
  TrendingUp,
  Package2,
  Activity,
  ChevronRight,
  RefreshCw,
  Clock
} from "lucide-react";
import { Panel, PanelHeader, PanelBody } from "@/components/ui/Panel";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import {
  getStateForecast,
  getAlerts,
  getStateStock,
} from "@/lib/api";


interface DistrictData {
  district_name: string;
  risk_level: string;
  risk_score: number;
  total_predicted_cases: number;
  peak_day: string;
}

interface AlertData {
  id: string;
  district_name: string;
  level: string;
  title: string;
  message: string;
  risk_score: number;
}

export default function CommandCenter() {
  const [stateData, setStateData] = useState<Record<string, DistrictData> | null>(null);
  const [alerts, setAlerts] = useState<{ count: number; summary: Record<string, number>; alerts: AlertData[] } | null>(null);
  const [stockData, setStockData] = useState<{ overall_readiness: number; summary: { critical_items: number } } | null>(null);
  const [loading, setLoading] = useState(true);
  const [lastUpdate, setLastUpdate] = useState<Date>(new Date());

  const fetchStateData = useCallback(async () => {
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
    } finally {
      setLoading(false);
    }
  }, []);

  const handleRefresh = useCallback(() => {
    setLoading(true);
    fetchStateData();
  }, [fetchStateData]);

  useEffect(() => {
    fetchStateData();
  }, [fetchStateData]);

  const districts = stateData ? Object.entries(stateData) : [];
  const redCount = districts.filter(([, d]) => d.risk_level === "red").length;
  const orangeCount = districts.filter(([, d]) => d.risk_level === "orange").length;
  const totalCases = districts.reduce((sum, [, d]) => sum + d.total_predicted_cases, 0);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <RefreshCw className="animate-spin text-accent" size={24} />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[var(--bg-base)]">
      {/* Page Header */}
      <header className="page-header">
        <div className="page-title">
          <span>Command Center</span>
          <span className="text-sm font-normal text-secondary">Rajasthan State</span>
        </div>
        <div className="page-meta">
          <div className="flex items-center gap-2">
            <Clock size={14} />
            <span>{lastUpdate.toLocaleTimeString()}</span>
          </div>
          <Button
            variant="ghost"
            size="sm"
            onClick={handleRefresh}
            disabled={loading}
            className="text-secondary hover:text-primary"
          >
            <RefreshCw size={14} className={cn("mr-2", loading && "animate-spin")} />
            Refresh
          </Button>
        </div>
      </header>

      <div className="p-8 space-y-8">
        {/* Metrics Row — Secondary importance */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
          <MetricCard
            icon={<AlertTriangle size={18} />}
            label="Elevated Risk"
            value={redCount + orangeCount}
            suffix="districts"
            variant={redCount > 0 ? "critical" : orangeCount > 0 ? "warning" : "default"}
          />
          <MetricCard
            icon={<TrendingUp size={18} />}
            label="14-Day Forecast"
            value={totalCases.toLocaleString()}
            suffix="cases"
          />
          <MetricCard
            icon={<Package2 size={18} />}
            label="Stock Readiness"
            value={stockData?.overall_readiness || 0}
            suffix="%"
            variant={
              (stockData?.overall_readiness || 0) < 50 ? "critical" :
                (stockData?.overall_readiness || 0) < 70 ? "warning" : "default"
            }
          />
          <MetricCard
            icon={<Activity size={18} />}
            label="Active Alerts"
            value={alerts?.count || 0}
            suffix="active"
          />
        </div>

        {/* District Table — THE HERO */}
        <Panel>
          <PanelHeader
            actions={
              <span className="text-sm text-muted">
                {districts.length} districts monitored
              </span>
            }
          >
            District Overview
          </PanelHeader>
          <PanelBody noPadding>
            <div className="overflow-x-auto">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>District</th>
                    <th>Risk Level</th>
                    <th>Risk Score</th>
                    <th>14-Day Forecast</th>
                    <th></th>
                  </tr>
                </thead>
                <tbody>
                  {districts
                    .sort((a, b) => {
                      const order: Record<string, number> = { red: 0, orange: 1, yellow: 2, green: 3 };
                      return order[a[1].risk_level] - order[b[1].risk_level];
                    })
                    .map(([id, district]) => (
                      <tr key={id}>
                        <td className="font-medium">{district.district_name}</td>
                        <td>
                          <RiskBadge level={district.risk_level} />
                        </td>
                        <td className="font-mono text-secondary">
                          {(district.risk_score * 100).toFixed(0)}%
                        </td>
                        <td className="font-mono text-secondary">
                          {district.total_predicted_cases} cases
                        </td>
                        <td>
                          <Link href={`/district/${id}`}>
                            <Button variant="ghost" size="icon" className="h-8 w-8 text-muted-foreground hover:text-accent">
                              <ChevronRight size={16} />
                            </Button>
                          </Link>
                        </td>
                      </tr>
                    ))}
                </tbody>
              </table>
            </div>
          </PanelBody>
        </Panel>
      </div>
    </div>
  );
}

/* ===== COMPONENTS ===== */

function MetricCard({
  icon,
  label,
  value,
  suffix,
  variant = "default"
}: {
  icon: React.ReactNode;
  label: string;
  value: string | number;
  suffix: string;
  variant?: 'critical' | 'warning' | 'default';
}) {
  const valueColor = {
    critical: 'text-critical',
    warning: 'text-warning',
    default: 'text-primary'
  };

  return (
    <div className="metric-card">
      <div className="flex items-center gap-2 mb-2">
        <span className="text-muted">{icon}</span>
        <span className="metric-label">{label}</span>
      </div>
      <div className="flex items-baseline gap-1">
        <span className={cn("metric-value", valueColor[variant])}>
          {value}
        </span>
        <span className="metric-suffix">{suffix}</span>
      </div>
    </div>
  );
}

function RiskBadge({ level }: { level: string }) {
  const config = {
    red: { label: 'Critical', class: 'risk-red' },
    orange: { label: 'Elevated', class: 'risk-orange' },
    yellow: { label: 'Watch', class: 'risk-yellow' },
    green: { label: 'Normal', class: 'risk-green' }
  };

  const { label, class: className } = config[level as keyof typeof config] || config.green;

  return (
    <span className={cn("risk-badge", className)}>
      <span className={cn(
        "status-dot",
        level === 'red' ? 'status-critical' :
          level === 'orange' ? 'status-warning' :
            level === 'yellow' ? 'status-warning' :
              'status-success'
      )} />
      {label}
    </span>
  );
}
