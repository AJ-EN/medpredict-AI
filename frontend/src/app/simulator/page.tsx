"use client";

import { useState, useEffect } from "react";
import {
    PlayCircle,
    AlertTriangle,
    TrendingDown,
    Clock,
    Heart,
    Zap
} from "lucide-react";
import { simulateScenario } from "@/lib/api";

export default function SimulatorPage() {
    const [severity, setSeverity] = useState(2);
    const [responseDays, setResponseDays] = useState(7);
    const [results, setResults] = useState<any>(null);
    const [loading, setLoading] = useState(false);

    useEffect(() => {
        runSimulation();
    }, []);

    async function runSimulation() {
        setLoading(true);
        try {
            const data = await simulateScenario(severity, responseDays);
            setResults(data);
        } catch (error) {
            console.error("Error running simulation:", error);
        }
        setLoading(false);
    }

    const presetScenarios = [
        { label: "Monsoon Delay", severity: 1.5, response: 10 },
        { label: "Double Intensity", severity: 3, response: 7 },
        { label: "Multi-District", severity: 5, response: 5 },
    ];

    return (
        <div>
            {/* Header */}
            <div style={{ marginBottom: 32 }}>
                <h1 style={{ fontSize: 28, fontWeight: 700, marginBottom: 4 }}>
                    🎮 Scenario Simulator
                </h1>
                <p style={{ color: "var(--muted)" }}>
                    Model outbreak scenarios and evaluate system effectiveness
                </p>
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "400px 1fr", gap: 24 }}>
                {/* Controls */}
                <div className="card">
                    <h2 style={{ fontSize: 16, fontWeight: 600, marginBottom: 24 }}>
                        ⚙️ Simulation Parameters
                    </h2>

                    {/* Severity Slider */}
                    <div style={{ marginBottom: 32 }}>
                        <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 12 }}>
                            <label style={{ fontWeight: 500 }}>Outbreak Severity</label>
                            <span style={{
                                color: severity > 5 ? "var(--danger)" : severity > 2 ? "var(--warning)" : "var(--success)",
                                fontWeight: 600
                            }}>
                                {severity}x baseline
                            </span>
                        </div>
                        <input
                            type="range"
                            min="1"
                            max="10"
                            step="0.5"
                            value={severity}
                            onChange={(e) => setSeverity(parseFloat(e.target.value))}
                            style={{ width: "100%" }}
                        />
                        <div style={{ display: "flex", justifyContent: "space-between", fontSize: 12, color: "var(--muted)", marginTop: 8 }}>
                            <span>1x (Normal)</span>
                            <span>10x (Severe)</span>
                        </div>
                    </div>

                    {/* Response Time Slider */}
                    <div style={{ marginBottom: 32 }}>
                        <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 12 }}>
                            <label style={{ fontWeight: 500 }}>Response Lead Time</label>
                            <span style={{
                                color: responseDays < 5 ? "var(--success)" : responseDays < 10 ? "var(--warning)" : "var(--danger)",
                                fontWeight: 600
                            }}>
                                {responseDays} days
                            </span>
                        </div>
                        <input
                            type="range"
                            min="0"
                            max="21"
                            step="1"
                            value={responseDays}
                            onChange={(e) => setResponseDays(parseInt(e.target.value))}
                            style={{ width: "100%" }}
                        />
                        <div style={{ display: "flex", justifyContent: "space-between", fontSize: 12, color: "var(--muted)", marginTop: 8 }}>
                            <span>0 days (Instant)</span>
                            <span>21 days (Traditional)</span>
                        </div>
                    </div>

                    {/* Preset Scenarios */}
                    <div style={{ marginBottom: 24 }}>
                        <label style={{ fontWeight: 500, display: "block", marginBottom: 12 }}>
                            Pre-set Scenarios
                        </label>
                        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                            {presetScenarios.map((scenario) => (
                                <button
                                    key={scenario.label}
                                    onClick={() => {
                                        setSeverity(scenario.severity);
                                        setResponseDays(scenario.response);
                                    }}
                                    className="btn btn-ghost"
                                    style={{ justifyContent: "flex-start" }}
                                >
                                    {scenario.label}
                                </button>
                            ))}
                        </div>
                    </div>

                    {/* Run Button */}
                    <button
                        onClick={runSimulation}
                        className="btn btn-primary"
                        style={{ width: "100%" }}
                        disabled={loading}
                    >
                        <PlayCircle size={18} />
                        {loading ? "Simulating..." : "Run Simulation"}
                    </button>
                </div>

                {/* Results */}
                <div className="card">
                    <h2 style={{ fontSize: 16, fontWeight: 600, marginBottom: 24 }}>
                        📊 Simulation Results
                    </h2>

                    {results && (
                        <div>
                            {/* Impact Cards */}
                            <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 16, marginBottom: 32 }}>
                                <ImpactCard
                                    icon={<AlertTriangle />}
                                    label="Stockouts Prevented"
                                    value={results.results?.impact?.stockouts_prevented || 0}
                                    color="var(--success)"
                                />
                                <ImpactCard
                                    icon={<Clock />}
                                    label="Days Saved"
                                    value={results.results?.impact?.response_time_saved_days || 0}
                                    color="var(--accent)"
                                />
                                <ImpactCard
                                    icon={<Heart />}
                                    label="Lives Impacted"
                                    value={results.results?.impact?.estimated_lives_impacted || 0}
                                    color="var(--danger)"
                                />
                            </div>

                            {/* Comparison */}
                            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 24 }}>
                                {/* Without System */}
                                <div style={{
                                    padding: 24,
                                    background: "rgba(239,68,68,0.1)",
                                    borderRadius: 12,
                                    border: "1px solid rgba(239,68,68,0.2)"
                                }}>
                                    <h3 style={{ fontSize: 14, fontWeight: 600, marginBottom: 16, color: "var(--danger)" }}>
                                        ❌ Without MedPredict
                                    </h3>
                                    <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
                                        <div style={{ display: "flex", justifyContent: "space-between" }}>
                                            <span style={{ color: "var(--muted)" }}>Stockout Events</span>
                                            <span style={{ fontWeight: 600 }}>{results.results?.without_system?.stockout_events}</span>
                                        </div>
                                        <div style={{ display: "flex", justifyContent: "space-between" }}>
                                            <span style={{ color: "var(--muted)" }}>Response Time</span>
                                            <span style={{ fontWeight: 600 }}>{results.results?.without_system?.response_time_days} days</span>
                                        </div>
                                        <div style={{ display: "flex", justifyContent: "space-between" }}>
                                            <span style={{ color: "var(--muted)" }}>Emergency Cost</span>
                                            <span style={{ fontWeight: 600 }}>₹{(results.results?.without_system?.estimated_cost / 100000).toFixed(1)}L</span>
                                        </div>
                                    </div>
                                </div>

                                {/* With System */}
                                <div style={{
                                    padding: 24,
                                    background: "rgba(34,197,94,0.1)",
                                    borderRadius: 12,
                                    border: "1px solid rgba(34,197,94,0.2)"
                                }}>
                                    <h3 style={{ fontSize: 14, fontWeight: 600, marginBottom: 16, color: "var(--success)" }}>
                                        ✅ With MedPredict
                                    </h3>
                                    <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
                                        <div style={{ display: "flex", justifyContent: "space-between" }}>
                                            <span style={{ color: "var(--muted)" }}>Stockout Events</span>
                                            <span style={{ fontWeight: 600 }}>{results.results?.with_system?.stockout_events}</span>
                                        </div>
                                        <div style={{ display: "flex", justifyContent: "space-between" }}>
                                            <span style={{ color: "var(--muted)" }}>Response Time</span>
                                            <span style={{ fontWeight: 600 }}>{results.results?.with_system?.response_time_days} days</span>
                                        </div>
                                        <div style={{ display: "flex", justifyContent: "space-between" }}>
                                            <span style={{ color: "var(--muted)" }}>Planned Cost</span>
                                            <span style={{ fontWeight: 600 }}>₹{(results.results?.with_system?.estimated_cost / 100000).toFixed(1)}L</span>
                                        </div>
                                    </div>
                                </div>
                            </div>

                            {/* Cost Savings */}
                            <div style={{
                                marginTop: 24,
                                padding: 20,
                                background: "linear-gradient(135deg, rgba(59,130,246,0.1) 0%, rgba(139,92,246,0.1) 100%)",
                                borderRadius: 12,
                                border: "1px solid rgba(59,130,246,0.2)",
                                textAlign: "center"
                            }}>
                                <div style={{ fontSize: 14, color: "var(--muted)", marginBottom: 8 }}>Total Cost Savings</div>
                                <div style={{ fontSize: 36, fontWeight: 700, color: "var(--success)" }}>
                                    ₹{((results.results?.impact?.cost_savings || 0) / 100000).toFixed(1)} Lakhs
                                </div>
                            </div>
                        </div>
                    )}
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
    color: string;
}) {
    return (
        <div style={{
            padding: 20,
            background: `${color}15`,
            borderRadius: 12,
            border: `1px solid ${color}30`,
            textAlign: "center"
        }}>
            <div style={{ color, marginBottom: 8 }}>{icon}</div>
            <div style={{ fontSize: 32, fontWeight: 700, color }}>{value}</div>
            <div style={{ fontSize: 13, color: "var(--muted)", marginTop: 4 }}>{label}</div>
        </div>
    );
}
