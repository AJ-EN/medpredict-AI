"use client";

import { useState, useEffect, useCallback } from "react";
import {
    Bell,
    TrendingUp,
    CloudRain,
    Calendar,
    Activity,
    RefreshCw,
    Clock
} from "lucide-react";
import { Panel, PanelHeader, PanelBody } from "@/components/ui/Panel";
import { cn } from "@/lib/utils";
import {
    getAlerts,
    getDistrictSignals
} from "@/lib/api";
import { Button } from "@/components/ui/button";

interface Alert {
    id: string;
    district_id: string;
    district_name: string;
    level: string;
    risk_score: number;
    message: string;
    signals: Record<string, number>;
}

interface Signals {
    district_name: string;
    overall_risk: { score: number; level: string };
    signals: {
        weather: { value: number; description: string; data: Record<string, number> };
        seasonal: { value: number; description: string };
        trend: { value: number; description: string };
    };
}

export default function ThreatDetection() {
    const [alerts, setAlerts] = useState<{ count: number; summary: Record<string, number>; alerts: Alert[] } | null>(null);
    const [selectedDistrict, setSelectedDistrict] = useState<string | null>(null);
    const [signals, setSignals] = useState<Signals | null>(null);
    const [loading, setLoading] = useState(true);

    const loadData = useCallback(async () => {
        try {
            const data = await getAlerts();
            setAlerts(data);
            if (data.alerts?.[0]) {
                setSelectedDistrict(data.alerts[0].district_id);
            }
        } catch (error) {
            console.error("Error loading alerts:", error);
        } finally {
            setLoading(false);
        }
    }, []);

    const loadSignals = useCallback(async (districtId: string) => {
        try {
            const data = await getDistrictSignals(districtId);
            setSignals(data);
        } catch (error) {
            console.error("Error loading signals:", error);
        }
    }, []);

    useEffect(() => {
        loadData();
    }, [loadData]);

    useEffect(() => {
        if (selectedDistrict) {
            loadSignals(selectedDistrict);
        }
    }, [selectedDistrict, loadSignals]);

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
                    <span>Threat Detection</span>
                    <div className="flex gap-2 ml-4">
                        {(alerts?.summary?.red || 0) > 0 && (
                            <span className="risk-badge risk-red">
                                {alerts?.summary?.red} critical
                            </span>
                        )}
                        {(alerts?.summary?.orange || 0) > 0 && (
                            <span className="risk-badge risk-orange">
                                {alerts?.summary?.orange} elevated
                            </span>
                        )}
                        {(alerts?.summary?.yellow || 0) > 0 && (
                            <span className="risk-badge risk-yellow">
                                {alerts?.summary?.yellow} watch
                            </span>
                        )}
                    </div>
                </div>
                <div className="page-meta">
                    <div className="flex items-center gap-2">
                        <Clock size={14} />
                        <span>{new Date().toLocaleTimeString()}</span>
                    </div>
                    <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => { setLoading(true); loadData(); }}
                        className="text-secondary hover:text-primary"
                    >
                        <RefreshCw size={14} className="mr-2" />
                        Refresh
                    </Button>
                </div>
            </header>

            <div className="p-6">
                <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                    {/* Alert List */}
                    <Panel>
                        <PanelHeader>
                            Active Alerts ({alerts?.count || 0})
                        </PanelHeader>
                        <PanelBody noPadding>
                            <div className="divide-y divide-[var(--border-muted)] max-h-[600px] overflow-y-auto">
                                {alerts?.alerts?.map((alert) => (
                                    <button
                                        key={alert.id}
                                        onClick={() => setSelectedDistrict(alert.district_id)}
                                        className={cn(
                                            "w-full text-left p-4 transition-colors",
                                            selectedDistrict === alert.district_id
                                                ? "bg-[var(--accent-muted)] border-l-2 border-l-[var(--accent)]"
                                                : "hover:bg-[var(--bg-elevated)] border-l-2 border-l-transparent"
                                        )}
                                    >
                                        <div className="flex items-center gap-3 mb-2">
                                            <span className={cn(
                                                "status-dot",
                                                alert.level === 'red' ? 'status-critical' :
                                                    alert.level === 'orange' ? 'status-warning' :
                                                        'status-muted'
                                            )} />
                                            <span className="font-medium">{alert.district_name}</span>
                                            <span className={cn(
                                                "text-sm font-mono ml-auto",
                                                alert.level === 'red' ? 'text-critical' :
                                                    alert.level === 'orange' ? 'text-warning' :
                                                        'text-muted'
                                            )}>
                                                {(alert.risk_score * 100).toFixed(0)}%
                                            </span>
                                        </div>
                                        <p className="text-sm text-secondary line-clamp-2">
                                            {alert.message}
                                        </p>
                                    </button>
                                ))}

                                {(!alerts?.alerts || alerts.alerts.length === 0) && (
                                    <div className="text-center py-16">
                                        <Bell size={32} className="mx-auto mb-3 text-muted opacity-40" />
                                        <p className="text-secondary">No active alerts</p>
                                        <p className="text-sm text-muted mt-1">All districts within normal parameters</p>
                                    </div>
                                )}
                            </div>
                        </PanelBody>
                    </Panel>

                    {/* Signal Analysis */}
                    <Panel className="lg:col-span-2">
                        <PanelHeader
                            actions={
                                signals && (
                                    <span className="text-sm text-muted">
                                        {signals.district_name}
                                    </span>
                                )
                            }
                        >
                            Signal Analysis
                        </PanelHeader>
                        <PanelBody>
                            {signals ? (
                                <div className="space-y-8">
                                    {/* Risk Score */}
                                    <div className={cn(
                                        "text-center p-8 rounded-lg border",
                                        signals.overall_risk?.level === 'red' ? 'bg-[var(--status-critical-muted)] border-[var(--status-critical)]' :
                                            signals.overall_risk?.level === 'orange' ? 'bg-[var(--status-warning-muted)] border-[var(--status-warning)]' :
                                                'bg-[var(--bg-elevated)] border-[var(--border)]'
                                    )}>
                                        <div className="text-sm text-muted uppercase tracking-wide mb-2">
                                            Composite Threat Score
                                        </div>
                                        <div className={cn(
                                            "text-5xl font-bold font-mono",
                                            signals.overall_risk?.level === 'red' ? 'text-critical' :
                                                signals.overall_risk?.level === 'orange' ? 'text-warning' :
                                                    'text-primary'
                                        )}>
                                            {((signals.overall_risk?.score || 0) * 100).toFixed(0)}%
                                        </div>
                                        <span className={cn(
                                            "inline-block mt-3 risk-badge",
                                            `risk-${signals.overall_risk?.level || 'green'}`
                                        )}>
                                            {(signals.overall_risk?.level || 'normal').toUpperCase()}
                                        </span>
                                    </div>

                                    {/* Signal Breakdown */}
                                    <div className="space-y-6">
                                        <SignalBar
                                            icon={<CloudRain size={18} />}
                                            label="Weather Signal"
                                            value={signals.signals?.weather?.value || 0}
                                            description={signals.signals?.weather?.description}
                                            note="14-day lagged"
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

                                    {/* Environmental Data */}
                                    {signals.signals?.weather?.data && (
                                        <div className="p-5 bg-[var(--bg-elevated)] rounded-lg">
                                            <div className="text-xs text-muted uppercase tracking-wide mb-4">
                                                Environmental Telemetry
                                            </div>
                                            <div className="grid grid-cols-3 gap-6">
                                                <div>
                                                    <div className="text-xs text-muted mb-1">Temperature</div>
                                                    <div className="text-xl font-mono">{signals.signals.weather.data.temperature?.toFixed(1)}°C</div>
                                                </div>
                                                <div>
                                                    <div className="text-xs text-muted mb-1">Rainfall (Lag)</div>
                                                    <div className="text-xl font-mono">{signals.signals.weather.data.rainfall_lag_14d?.toFixed(0) || 0}mm</div>
                                                </div>
                                                <div>
                                                    <div className="text-xs text-muted mb-1">Humidity</div>
                                                    <div className="text-xl font-mono">{signals.signals.weather.data.humidity?.toFixed(0)}%</div>
                                                </div>
                                            </div>
                                        </div>
                                    )}
                                </div>
                            ) : (
                                <div className="text-center py-16">
                                    <Activity size={32} className="mx-auto mb-3 text-muted opacity-40" />
                                    <p className="text-secondary">Select an alert to view analysis</p>
                                </div>
                            )}
                        </PanelBody>
                    </Panel>
                </div>
            </div>
        </div>
    );
}

function SignalBar({
    icon,
    label,
    value,
    description,
    note
}: {
    icon: React.ReactNode;
    label: string;
    value: number;
    description?: string;
    note?: string;
}) {
    const percentage = (value * 100).toFixed(0);

    const getBarColor = (val: number) => {
        if (val > 0.7) return 'bg-[var(--status-critical)]';
        if (val > 0.5) return 'bg-[var(--status-warning)]';
        return 'bg-[var(--accent)]';
    };

    return (
        <div>
            <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-3">
                    <span className="text-muted">{icon}</span>
                    <span className="font-medium">{label}</span>
                    {note && (
                        <span className="text-xs text-accent bg-[var(--accent-muted)] px-2 py-0.5 rounded">
                            {note}
                        </span>
                    )}
                </div>
                <span className="font-mono text-lg">{percentage}%</span>
            </div>
            <div className="h-2 bg-[var(--bg-elevated)] rounded-full overflow-hidden">
                <div
                    className={cn("h-full transition-all duration-500 rounded-full", getBarColor(value))}
                    style={{ width: `${percentage}%` }}
                />
            </div>
            {description && (
                <p className="text-sm text-secondary mt-2">{description}</p>
            )}
        </div>
    );
}
