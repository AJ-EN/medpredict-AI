"use client";

import { useState, useEffect, useCallback } from "react";
import {
    Zap,
    AlertTriangle,
    Clock,
    Heart,
    RefreshCw
} from "lucide-react";
import { Panel, PanelHeader, PanelBody } from "@/components/ui/Panel";
import { Slider } from "@/components/ui/slider";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { simulateScenario } from "@/lib/api";

interface SimulationResults {
    results: {
        without_system: {
            stockout_events: number;
            response_time_days: number;
            estimated_cost: number;
        };
        with_system: {
            stockout_events: number;
            response_time_days: number;
            estimated_cost: number;
        };
        impact: {
            stockouts_prevented: number;
            response_time_saved_days: number;
            estimated_lives_impacted: number;
            cost_savings: number;
        };
    };
}

export default function ScenarioEngine() {
    const [severity, setSeverity] = useState(2);
    const [responseDays, setResponseDays] = useState(7);
    const [results, setResults] = useState<SimulationResults | null>(null);
    const [loading, setLoading] = useState(false);

    const runSimulation = useCallback(async () => {
        try {
            const data = await simulateScenario(severity, responseDays);
            setResults(data);
        } catch (error) {
            console.error("Error running simulation:", error);
        } finally {
            setLoading(false);
        }
    }, [severity, responseDays]);

    const handleRun = () => {
        setLoading(true);
        runSimulation();
    };

    useEffect(() => {
        // Initial run - loading defaults to false here? 
        // Logic: The page starts with loading=false. But we want to run initially?
        // Actually earlier loading=false.
        // Let's set loading=true on mount if we want to show it.
        // But the previous code just ran it.
        runSimulation();
    }, [runSimulation]);

    const presetScenarios = [
        { label: "Monsoon Delay", severity: 1.5, response: 10, description: "Late onset, prolonged risk period" },
        { label: "Double Intensity", severity: 3, response: 7, description: "2x normal outbreak scale" },
        { label: "Multi-District", severity: 5, response: 5, description: "Simultaneous regional surge" },
    ];

    const getSeverityLabel = (val: number) => {
        if (val <= 1.5) return { text: 'Mild', class: 'text-success' };
        if (val <= 3) return { text: 'Moderate', class: 'text-warning' };
        if (val <= 5) return { text: 'Severe', class: 'text-warning' };
        return { text: 'Extreme', class: 'text-critical' };
    };

    const severityInfo = getSeverityLabel(severity);

    return (
        <div className="min-h-screen bg-[var(--bg-base)]">
            {/* Page Header */}
            <header className="page-header">
                <div className="page-title">
                    <span>Scenario Engine</span>
                    <span className="text-sm font-normal text-muted ml-2">What-if Analysis</span>
                </div>
                <div className="page-meta">
                    <button
                        onClick={runSimulation}
                        disabled={loading}
                        className="flex items-center gap-2 px-3 py-1.5 text-sm text-secondary hover:text-primary hover:bg-[var(--bg-elevated)] rounded-md transition-colors"
                    >
                        <RefreshCw size={14} className={cn(loading && "animate-spin")} />
                        Recalculate
                    </button>
                </div>
            </header>

            <div className="p-6">
                <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                    {/* Controls */}
                    <Panel>
                        <PanelHeader>Simulation Parameters</PanelHeader>
                        <PanelBody className="space-y-8">
                            {/* Severity Slider */}
                            <div>
                                <div className="flex items-center justify-between mb-4">
                                    <label className="text-sm font-medium text-secondary">Outbreak Severity</label>
                                    <span className={cn("text-xl font-mono font-semibold", severityInfo.class)}>
                                        {severity}x
                                    </span>
                                </div>
                                <Slider
                                    value={[severity]}
                                    onValueChange={(vals) => setSeverity(vals[0])}
                                    min={1}
                                    max={10}
                                    step={0.5}
                                    className="w-full"
                                />
                                <div className="flex justify-between text-xs text-muted mt-2">
                                    <span>1× Baseline</span>
                                    <span className={severityInfo.class}>{severityInfo.text}</span>
                                    <span>10× Pandemic</span>
                                </div>
                            </div>

                            {/* Response Time Slider */}
                            <div>
                                <div className="flex items-center justify-between mb-4">
                                    <label className="text-sm font-medium text-secondary">Response Lead Time</label>
                                    <span className={cn(
                                        "text-xl font-mono font-semibold",
                                        responseDays <= 5 ? 'text-success' :
                                            responseDays <= 10 ? 'text-warning' :
                                                'text-critical'
                                    )}>
                                        {responseDays} days
                                    </span>
                                </div>
                                <Slider
                                    value={[responseDays]}
                                    onValueChange={(vals) => setResponseDays(vals[0])}
                                    min={0}
                                    max={21}
                                    step={1}
                                    className="w-full"
                                />
                                <div className="flex justify-between text-xs text-muted mt-2">
                                    <span>0d Instant</span>
                                    <span>21d Traditional</span>
                                </div>
                            </div>

                            {/* Presets */}
                            <div>
                                <label className="text-sm font-medium text-secondary block mb-3">Preset Scenarios</label>
                                <div className="space-y-2">
                                    {presetScenarios.map((scenario) => (
                                        <button
                                            key={scenario.label}
                                            onClick={() => {
                                                setSeverity(scenario.severity);
                                                setResponseDays(scenario.response);
                                            }}
                                            className="w-full p-4 text-left rounded-lg border border-[var(--border)] bg-[var(--bg-elevated)] hover:bg-[var(--bg-surface)] hover:border-[var(--accent)] transition-colors"
                                        >
                                            <div className="font-medium">{scenario.label}</div>
                                            <div className="text-sm text-muted mt-1">{scenario.description}</div>
                                        </button>
                                    ))}
                                </div>
                            </div>

                            {/* Run Button */}
                            <Button
                                onClick={handleRun}
                                disabled={loading}
                                className="w-full"
                                size="lg"
                            >
                                <Zap size={18} className="mr-2" />
                                {loading ? "Simulating..." : "Run Simulation"}
                            </Button>
                        </PanelBody>
                    </Panel>

                    {/* Results — THE HERO */}
                    <Panel className="lg:col-span-2">
                        <PanelHeader>Simulation Results</PanelHeader>
                        <PanelBody>
                            {results && (
                                <div className="space-y-8">
                                    {/* Impact Metrics — Primary Focus */}
                                    <div className="grid grid-cols-3 gap-6">
                                        <ImpactCard
                                            icon={<AlertTriangle size={20} />}
                                            label="Stockouts Prevented"
                                            value={results.results?.impact?.stockouts_prevented || 0}
                                            color="success"
                                        />
                                        <ImpactCard
                                            icon={<Clock size={20} />}
                                            label="Days Saved"
                                            value={results.results?.impact?.response_time_saved_days || 0}
                                            color="accent"
                                        />
                                        <ImpactCard
                                            icon={<Heart size={20} />}
                                            label="Lives Impacted"
                                            value={results.results?.impact?.estimated_lives_impacted || 0}
                                            color="critical"
                                        />
                                    </div>

                                    {/* Comparison */}
                                    <div className="grid grid-cols-2 gap-6">
                                        {/* Without System */}
                                        <div className="p-6 rounded-lg border border-[var(--status-critical)] bg-[var(--bg-elevated)]">
                                            <div className="flex items-center gap-2 mb-5">
                                                <span className="status-dot status-critical" />
                                                <span className="font-medium">Without MedPredict</span>
                                            </div>
                                            <div className="space-y-4">
                                                <StatRow
                                                    label="Stockout Events"
                                                    value={results.results?.without_system?.stockout_events}
                                                />
                                                <StatRow
                                                    label="Response Time"
                                                    value={`${results.results?.without_system?.response_time_days} days`}
                                                />
                                                <StatRow
                                                    label="Emergency Cost"
                                                    value={`₹${((results.results?.without_system?.estimated_cost || 0) / 100000).toFixed(1)}L`}
                                                />
                                            </div>
                                        </div>

                                        {/* With System */}
                                        <div className="p-6 rounded-lg border border-[var(--status-success)] bg-[var(--bg-elevated)]">
                                            <div className="flex items-center gap-2 mb-5">
                                                <span className="status-dot status-success" />
                                                <span className="font-medium">With MedPredict</span>
                                            </div>
                                            <div className="space-y-4">
                                                <StatRow
                                                    label="Stockout Events"
                                                    value={results.results?.with_system?.stockout_events}
                                                />
                                                <StatRow
                                                    label="Response Time"
                                                    value={`${results.results?.with_system?.response_time_days} days`}
                                                />
                                                <StatRow
                                                    label="Planned Cost"
                                                    value={`₹${((results.results?.with_system?.estimated_cost || 0) / 100000).toFixed(1)}L`}
                                                />
                                            </div>
                                        </div>
                                    </div>

                                    {/* Total Savings */}
                                    <div className="p-8 rounded-lg border border-[var(--accent)] bg-[var(--accent-muted)] text-center">
                                        <div className="text-sm text-muted uppercase tracking-wide mb-2">
                                            Total Cost Savings
                                        </div>
                                        <div className="text-4xl font-bold font-mono text-accent">
                                            ₹{((results.results?.impact?.cost_savings || 0) / 100000).toFixed(1)} Lakhs
                                        </div>
                                        <div className="text-sm text-secondary mt-3">
                                            Through proactive pre-positioning and network optimization
                                        </div>
                                    </div>
                                </div>
                            )}
                        </PanelBody>
                    </Panel>
                </div>
            </div>
        </div>
    );
}

function ImpactCard({
    icon,
    label,
    value,
    color
}: {
    icon: React.ReactNode;
    label: string;
    value: number;
    color: 'success' | 'accent' | 'critical';
}) {
    const colorClasses = {
        success: 'text-success',
        accent: 'text-accent',
        critical: 'text-critical'
    };

    return (
        <div className="p-6 bg-[var(--bg-elevated)] rounded-lg text-center">
            <div className={cn("mb-3 flex justify-center", colorClasses[color])}>
                {icon}
            </div>
            <div className={cn("text-3xl font-bold font-mono", colorClasses[color])}>
                {value}
            </div>
            <div className="text-xs text-muted uppercase tracking-wide mt-2">{label}</div>
        </div>
    );
}

function StatRow({ label, value }: { label: string; value: string | number }) {
    return (
        <div className="flex justify-between items-center">
            <span className="text-sm text-secondary">{label}</span>
            <span className="font-mono font-medium">{value}</span>
        </div>
    );
}
