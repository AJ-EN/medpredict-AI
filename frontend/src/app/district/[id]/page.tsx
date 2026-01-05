"use client";

import { useState, useEffect, useCallback } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import {
    ArrowLeft,
    TrendingUp,
    Thermometer,
    CloudRain,
    Droplets,
    RefreshCw,
    Clock,
    AlertTriangle,
    CheckCircle2
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
import { Panel, PanelHeader, PanelBody } from "@/components/ui/Panel";
import { cn } from "@/lib/utils";
import {
    getDistrictForecast,
    getDistrictStock,
    getRecommendations,
    getDistrictSignals
} from "@/lib/api";
import { Button } from "@/components/ui/button";

interface StockItem {
    medicine_id: string;
    medicine_name: string;
    stock_percentage: number;
    current_stock: number;
    days_until_stockout: number;
    status: string;
}

interface Recommendation {
    priority: string;
    action: string;
    reason: string;
    deadline: string;
}

export default function DistrictAnalysis() {
    const params = useParams();
    const districtId = params.id as string;

    const [forecast, setForecast] = useState<{
        district_name: string;
        risk: { level: string; score: number };
        forecast: Array<{ date: string; predicted: number; upper_bound: number; lower_bound: number; is_causal?: boolean }>;
    } | null>(null);
    const [stock, setStock] = useState<{ stock_items: StockItem[] } | null>(null);
    const [recommendations, setRecommendations] = useState<{ recommendations: Recommendation[] } | null>(null);
    const [signals, setSignals] = useState<{
        signals: {
            weather: { data: { temperature: number; humidity: number; rainfall_lag_14d?: number; is_real_data?: boolean } };
        };
        overall_risk: { score: number };
    } | null>(null);
    const [loading, setLoading] = useState(true);

    const loadData = useCallback(async () => {
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
        } finally {
            setLoading(false);
        }
    }, [districtId]);

    useEffect(() => {
        loadData();
    }, [loadData]);

    if (loading) {
        return (
            <div className="min-h-screen flex items-center justify-center">
                <RefreshCw className="animate-spin text-accent" size={24} />
            </div>
        );
    }

    const riskLevel = forecast?.risk?.level || 'green';
    const riskScore = forecast?.risk?.score || 0;

    return (
        <div className="min-h-screen bg-[var(--bg-base)]">
            {/* Page Header */}
            <header className="page-header">
                <div className="page-title">
                    <Link href="/" className="text-muted hover:text-primary transition-colors">
                        <ArrowLeft size={18} />
                    </Link>
                    <span>{forecast?.district_name || districtId}</span>
                    <RiskBadge level={riskLevel} />
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

            <div className="p-6 space-y-6">
                {/* Signal Indicators — Compact row */}
                <div className="grid grid-cols-2 lg:grid-cols-4 gap-6">
                    <SignalCard
                        icon={<Thermometer size={16} />}
                        label="Temperature"
                        value={signals?.signals?.weather?.data?.temperature?.toFixed(1) || '--'}
                        unit="°C"
                        isLive={signals?.signals?.weather?.data?.is_real_data}
                    />
                    <SignalCard
                        icon={<CloudRain size={16} />}
                        label="Rainfall (14d lag)"
                        value={signals?.signals?.weather?.data?.rainfall_lag_14d?.toFixed(0) || '--'}
                        unit="mm"
                        highlight
                    />
                    <SignalCard
                        icon={<Droplets size={16} />}
                        label="Humidity"
                        value={signals?.signals?.weather?.data?.humidity?.toFixed(0) || '--'}
                        unit="%"
                    />
                    <SignalCard
                        icon={<TrendingUp size={16} />}
                        label="Risk Score"
                        value={(riskScore * 100).toFixed(0)}
                        unit="%"
                        status={riskLevel as 'red' | 'orange' | 'yellow' | 'green'}
                    />
                </div>

                {/* Main Content Grid */}
                <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                    {/* Forecast Chart — THE HERO */}
                    <Panel className="lg:col-span-2">
                        <PanelHeader
                            actions={
                                <span className="text-sm text-muted">
                                    Causal Model • 14-day forecast
                                </span>
                            }
                        >
                            Case Projection
                        </PanelHeader>
                        <PanelBody>
                            <div className="h-[320px]">
                                <ResponsiveContainer width="100%" height="100%">
                                    <AreaChart data={forecast?.forecast || []}>
                                        <defs>
                                            <linearGradient id="colorPredicted" x1="0" y1="0" x2="0" y2="1">
                                                <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3} />
                                                <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
                                            </linearGradient>
                                        </defs>
                                        <CartesianGrid strokeDasharray="3 3" stroke="#27272a" />
                                        <XAxis
                                            dataKey="date"
                                            tick={{ fill: '#a1a1aa', fontSize: 11 }}
                                            tickFormatter={(val) => new Date(val).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
                                            stroke="#3f3f46"
                                        />
                                        <YAxis
                                            tick={{ fill: '#a1a1aa', fontSize: 11 }}
                                            stroke="#3f3f46"
                                        />
                                        <Tooltip
                                            contentStyle={{
                                                background: '#18181b',
                                                border: '1px solid #3f3f46',
                                                borderRadius: 6,
                                                fontSize: 13,
                                                color: '#fafafa'
                                            }}
                                            labelFormatter={(val) => new Date(val).toLocaleDateString()}
                                        />
                                        <Area
                                            type="monotone"
                                            dataKey="upper_bound"
                                            stroke="transparent"
                                            fill="#3b82f6"
                                            fillOpacity={0.15}
                                        />
                                        <Area
                                            type="monotone"
                                            dataKey="lower_bound"
                                            stroke="transparent"
                                            fill="#0a0a0a"
                                        />
                                        <Line
                                            type="monotone"
                                            dataKey="predicted"
                                            stroke="#3b82f6"
                                            strokeWidth={2}
                                            dot={false}
                                        />
                                    </AreaChart>
                                </ResponsiveContainer>
                            </div>
                            <div className="flex gap-6 mt-4 justify-center text-xs text-muted">
                                <div className="flex items-center gap-2">
                                    <div className="w-4 h-0.5 bg-blue-500 rounded" />
                                    <span>Predicted Cases</span>
                                </div>
                                <div className="flex items-center gap-2">
                                    <div className="w-4 h-3 bg-blue-500 opacity-20 rounded" />
                                    <span>95% Confidence</span>
                                </div>
                            </div>
                        </PanelBody>
                    </Panel>

                    {/* Stock Status */}
                    <Panel>
                        <PanelHeader>Stock Readiness</PanelHeader>
                        <PanelBody className="space-y-4">
                            {stock?.stock_items?.map((item) => (
                                <div key={item.medicine_id}>
                                    <div className="flex items-center justify-between mb-2">
                                        <span className="text-sm font-medium truncate flex-1">{item.medicine_name}</span>
                                        <span className={cn(
                                            "text-sm font-mono ml-2",
                                            item.status === 'critical' ? 'text-critical' :
                                                item.status === 'warning' ? 'text-warning' :
                                                    'text-success'
                                        )}>
                                            {item.stock_percentage}%
                                        </span>
                                    </div>
                                    <div className="h-1.5 bg-[var(--bg-elevated)] rounded-full overflow-hidden">
                                        <div
                                            className={cn(
                                                "h-full transition-all duration-500 rounded-full",
                                                item.status === 'critical' ? 'bg-[var(--status-critical)]' :
                                                    item.status === 'warning' ? 'bg-[var(--status-warning)]' :
                                                        'bg-[var(--status-success)]'
                                            )}
                                            style={{ width: `${Math.min(item.stock_percentage, 100)}%` }}
                                        />
                                    </div>
                                    <div className="text-xs text-muted mt-1">
                                        {item.current_stock.toLocaleString()} units • {item.days_until_stockout}d runway
                                    </div>
                                </div>
                            ))}
                        </PanelBody>
                    </Panel>
                </div>

                {/* Recommendations — Only show if there are urgent items */}
                {recommendations?.recommendations && recommendations.recommendations.length > 0 && (
                    <Panel>
                        <PanelHeader>Recommended Actions</PanelHeader>
                        <PanelBody noPadding>
                            <div className="divide-y divide-[var(--border-muted)]">
                                {recommendations.recommendations.map((rec, i) => (
                                    <div key={i} className="flex items-start gap-4 p-5">
                                        <div className={cn(
                                            "w-8 h-8 rounded-md flex items-center justify-center flex-shrink-0",
                                            rec.priority === 'urgent' ? 'bg-[var(--status-critical-muted)]' :
                                                rec.priority === 'high' ? 'bg-[var(--status-warning-muted)]' :
                                                    'bg-[var(--bg-elevated)]'
                                        )}>
                                            {rec.priority === 'urgent' ? (
                                                <AlertTriangle size={16} className="text-critical" />
                                            ) : (
                                                <CheckCircle2 size={16} className="text-muted" />
                                            )}
                                        </div>
                                        <div className="flex-1 min-w-0">
                                            <div className="flex items-center gap-2 mb-1">
                                                <span className={cn(
                                                    "text-xs font-medium uppercase px-2 py-0.5 rounded",
                                                    rec.priority === 'urgent' ? 'bg-[var(--status-critical-muted)] text-critical' :
                                                        rec.priority === 'high' ? 'bg-[var(--status-warning-muted)] text-warning' :
                                                            'bg-[var(--bg-elevated)] text-muted'
                                                )}>
                                                    {rec.priority}
                                                </span>
                                            </div>
                                            <p className="font-medium">{rec.action}</p>
                                            <p className="text-sm text-secondary mt-1">{rec.reason}</p>
                                        </div>
                                        <div className="text-xs text-muted font-mono">
                                            {new Date(rec.deadline).toLocaleDateString()}
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </PanelBody>
                    </Panel>
                )}

                {/* Empty state for recommendations */}
                {(!recommendations?.recommendations || recommendations.recommendations.length === 0) && (
                    <Panel>
                        <PanelBody className="text-center py-12">
                            <CheckCircle2 size={32} className="mx-auto mb-3 text-success opacity-60" />
                            <p className="text-secondary">No urgent actions required</p>
                            <p className="text-sm text-muted mt-1">All metrics within normal parameters</p>
                        </PanelBody>
                    </Panel>
                )}
            </div>
        </div>
    );
}

/* ===== COMPONENTS ===== */

function SignalCard({
    icon,
    label,
    value,
    unit,
    highlight,
    status,
    isLive
}: {
    icon: React.ReactNode;
    label: string;
    value: string;
    unit: string;
    highlight?: boolean;
    status?: 'red' | 'orange' | 'yellow' | 'green';
    isLive?: boolean;
}) {
    const statusColors = {
        red: 'text-critical',
        orange: 'text-warning',
        yellow: 'text-warning',
        green: 'text-success'
    };

    return (
        <div className={cn(
            "metric-card relative",
            highlight && "border-[var(--accent)] border-opacity-50"
        )}>
            {isLive && (
                <div className="absolute top-2 right-2 flex items-center gap-1 bg-green-500/10 px-1.5 py-0.5 rounded text-[10px] text-green-500 font-medium animate-pulse">
                    <div className="w-1.5 h-1.5 rounded-full bg-green-500" />
                    LIVE
                </div>
            )}
            <div className="flex items-center gap-2 mb-2">
                <span className="text-muted">{icon}</span>
                <span className="text-xs text-muted uppercase tracking-wide">{label}</span>
            </div>
            <div className="flex items-baseline gap-1">
                <span className={cn(
                    "text-2xl font-semibold font-mono",
                    status ? statusColors[status] : 'text-primary'
                )}>
                    {value}
                </span>
                <span className="text-sm text-muted">{unit}</span>
            </div>
            {highlight && (
                <div className="text-xs text-accent mt-1">Causal indicator</div>
            )}
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
