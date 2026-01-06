"use client";

import { useState, useEffect, useCallback } from "react";
import {
    Shield,
    Truck,
    PackageCheck,
    AlertTriangle,
    CheckCircle2,
    Clock,
    RefreshCw,
    ArrowRight,
    Hash,
    XCircle,
    Plus,
    Zap,
    X
} from "lucide-react";
import { Panel, PanelHeader, PanelBody } from "@/components/ui/Panel";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import {
    getTransfers,
    getAnomalousTransfers,
    createTransfer,
    recordPickup,
    recordDelivery,
    type Transfer
} from "@/lib/api";

interface TransferWithAnomalies {
    transfer: Transfer;
    anomalies: Array<{ type: string; severity: string; message: string }>;
}

// District and medicine options
const DISTRICTS = [
    { id: "RJ-JP", name: "Jaipur" },
    { id: "RJ-JD", name: "Jodhpur" },
    { id: "RJ-UD", name: "Udaipur" },
    { id: "RJ-KT", name: "Kota" },
    { id: "RJ-AJ", name: "Ajmer" },
    { id: "RJ-BR", name: "Barmer" },
    { id: "RJ-BK", name: "Bikaner" },
    { id: "RJ-AL", name: "Alwar" },
    { id: "RJ-SR", name: "Sikar" },
    { id: "RJ-PL", name: "Pali" },
    { id: "RJ-BW", name: "Bhilwara" },
    { id: "RJ-GN", name: "Ganganagar" }
];

const MEDICINES = [
    { id: "PARA-500", name: "Paracetamol 500mg" },
    { id: "ORS-WHO", name: "ORS WHO Formula" },
    { id: "IV-RL", name: "IV Ringer Lactate" },
    { id: "DOXY-100", name: "Doxycycline 100mg" },
    { id: "ACT-AL", name: "Artemether-Lumefantrine" }
];

export default function TransfersDashboard() {
    const [transfers, setTransfers] = useState<Transfer[]>([]);
    const [anomalies, setAnomalies] = useState<TransferWithAnomalies[]>([]);
    const [statusCounts, setStatusCounts] = useState<Record<string, number>>({});
    const [loading, setLoading] = useState(true);
    const [selectedTransfer, setSelectedTransfer] = useState<Transfer | null>(null);
    const [showCreateForm, setShowCreateForm] = useState(false);
    const [demoLoading, setDemoLoading] = useState(false);

    const loadData = useCallback(async () => {
        try {
            const [transfersRes, anomaliesRes] = await Promise.all([
                getTransfers(),
                getAnomalousTransfers()
            ]);
            setTransfers(transfersRes.transfers || []);
            setStatusCounts(transfersRes.summary?.by_status || {});
            setAnomalies(anomaliesRes.anomalous_transfers || []);
        } catch (error) {
            console.error("Error loading transfers:", error);
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        loadData();
    }, [loadData]);

    const handleRefresh = () => {
        setLoading(true);
        loadData();
    };

    // Demo Mode: Create a complete transfer scenario
    const runDemoMode = async () => {
        setDemoLoading(true);
        try {
            // 1. Create a verified transfer
            const t1 = await createTransfer({
                medicine_id: "PARA-500",
                quantity: 2000,
                from_district_id: "RJ-JP",
                to_district_id: "RJ-KT",
                priority: "urgent",
                created_by: "DEMO-CMO-JAIPUR"
            });

            // Pickup
            await recordPickup(t1.transfer.id, {
                transporter_id: "DEMO-VEHICLE-001"
            });

            // Deliver (same quantity = verified)
            await recordDelivery(t1.transfer.id, {
                receiver_id: "DEMO-CMO-KOTA",
                received_quantity: 2000
            });

            // 2. Create a disputed transfer (quantity mismatch)
            const t2 = await createTransfer({
                medicine_id: "IV-RL",
                quantity: 800,
                from_district_id: "RJ-UD",
                to_district_id: "RJ-AJ",
                priority: "critical",
                created_by: "DEMO-CMO-UDAIPUR"
            });

            await recordPickup(t2.transfer.id, {
                transporter_id: "DEMO-VEHICLE-002"
            });

            // Deliver with 100 units missing!
            await recordDelivery(t2.transfer.id, {
                receiver_id: "DEMO-CMO-AJMER",
                received_quantity: 700,
                receiver_notes: "100 units missing on arrival"
            });

            // 3. Create a pending transfer (only created)
            await createTransfer({
                medicine_id: "ORS-WHO",
                quantity: 500,
                from_district_id: "RJ-BK",
                to_district_id: "RJ-GN",
                priority: "normal",
                created_by: "DEMO-CMO-BIKANER"
            });

            // Reload data
            await loadData();
            alert("✅ Demo Mode Complete!\n\n• 1 Verified Transfer\n• 1 Disputed Transfer (100 units missing)\n• 1 Pending Transfer");
        } catch (error) {
            console.error("Demo mode error:", error);
            alert("Error running demo mode");
        } finally {
            setDemoLoading(false);
        }
    };

    if (loading) {
        return (
            <div className="min-h-screen flex items-center justify-center">
                <RefreshCw className="animate-spin text-accent" size={24} />
            </div>
        );
    }

    const verifiedCount = statusCounts['verified'] || 0;
    const pendingCount = (statusCounts['created'] || 0) + (statusCounts['picked_up'] || 0);
    const disputedCount = statusCounts['disputed'] || 0;

    return (
        <div className="min-h-screen bg-[var(--bg-base)]">
            {/* Page Header */}
            <header className="page-header">
                <div className="page-title">
                    <Shield size={18} className="text-blue-500" />
                    <span>Transfer Verification</span>
                    <span className="text-sm font-normal text-muted ml-2">Chain of Custody</span>
                </div>
                <div className="page-meta">
                    <Button
                        variant="ghost"
                        size="sm"
                        onClick={runDemoMode}
                        disabled={demoLoading}
                        className="text-yellow-500 hover:text-yellow-400 hover:bg-yellow-500/10"
                    >
                        <Zap size={14} className={cn("mr-2", demoLoading && "animate-pulse")} />
                        {demoLoading ? "Running..." : "Demo Mode"}
                    </Button>
                    <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => setShowCreateForm(true)}
                        className="text-green-500 hover:text-green-400 hover:bg-green-500/10"
                    >
                        <Plus size={14} className="mr-2" />
                        New Transfer
                    </Button>
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

            <div className="p-6 space-y-6">
                {/* Status Overview */}
                <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
                    <StatusCard
                        icon={<PackageCheck size={20} />}
                        label="Verified"
                        value={verifiedCount}
                        color="success"
                    />
                    <StatusCard
                        icon={<Truck size={20} />}
                        label="In Transit"
                        value={pendingCount}
                        color="warning"
                    />
                    <StatusCard
                        icon={<XCircle size={20} />}
                        label="Disputed"
                        value={disputedCount}
                        color="critical"
                    />
                    <StatusCard
                        icon={<Hash size={20} />}
                        label="Total"
                        value={transfers.length}
                        color="default"
                    />
                </div>

                {/* Alert Banner for Anomalies */}
                {anomalies.length > 0 && (
                    <div className="p-4 rounded-lg border border-[var(--status-critical)] bg-[var(--status-critical)]/10">
                        <div className="flex items-start gap-3">
                            <AlertTriangle size={20} className="text-critical flex-shrink-0 mt-0.5" />
                            <div>
                                <div className="font-medium text-critical">
                                    {anomalies.length} Transfer{anomalies.length > 1 ? 's' : ''} with Discrepancies Detected
                                </div>
                                <div className="text-sm text-secondary mt-1">
                                    {anomalies.map(a => a.anomalies[0]?.message).join(' • ')}
                                </div>
                            </div>
                        </div>
                    </div>
                )}

                <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                    {/* Transfer List */}
                    <Panel className="lg:col-span-2">
                        <PanelHeader
                            actions={
                                <span className="text-sm text-muted">
                                    {transfers.length} transfers
                                </span>
                            }
                        >
                            All Transfers
                        </PanelHeader>
                        <PanelBody noPadding>
                            <div className="divide-y divide-[var(--border-muted)] max-h-[600px] overflow-y-auto">
                                {transfers.map((transfer) => (
                                    <button
                                        key={transfer.id}
                                        onClick={() => setSelectedTransfer(transfer)}
                                        className={cn(
                                            "w-full text-left p-4 transition-colors hover:bg-[var(--bg-elevated)]",
                                            selectedTransfer?.id === transfer.id && "bg-[var(--accent-muted)]"
                                        )}
                                    >
                                        <div className="flex items-center justify-between mb-2">
                                            <div className="flex items-center gap-2">
                                                <StatusBadge status={transfer.status} />
                                                <span className="font-mono text-sm">{transfer.id}</span>
                                            </div>
                                            <PriorityBadge priority={transfer.priority} />
                                        </div>
                                        <div className="flex items-center gap-2 text-sm text-secondary">
                                            <span>{transfer.from_district_id}</span>
                                            <ArrowRight size={14} />
                                            <span>{transfer.to_district_id}</span>
                                            <span className="text-muted">•</span>
                                            <span>{transfer.quantity} units</span>
                                        </div>
                                        {transfer.has_discrepancy && (
                                            <div className="flex items-center gap-1 mt-2 text-critical text-xs">
                                                <AlertTriangle size={12} />
                                                <span>{transfer.discrepancy_notes}</span>
                                            </div>
                                        )}
                                    </button>
                                ))}

                                {transfers.length === 0 && (
                                    <div className="text-center py-16">
                                        <Truck size={32} className="mx-auto mb-3 text-muted opacity-40" />
                                        <p className="text-secondary">No transfers yet</p>
                                        <p className="text-sm text-muted mt-1">Click "Demo Mode" or "New Transfer" to get started</p>
                                    </div>
                                )}
                            </div>
                        </PanelBody>
                    </Panel>

                    {/* Transfer Details */}
                    <Panel>
                        <PanelHeader>Chain of Custody</PanelHeader>
                        <PanelBody>
                            {selectedTransfer ? (
                                <div className="space-y-6">
                                    {/* Verification Status */}
                                    <div className={cn(
                                        "p-4 rounded-lg text-center",
                                        selectedTransfer.is_verified
                                            ? "bg-green-500/10 border border-green-500/30"
                                            : selectedTransfer.has_discrepancy
                                                ? "bg-red-500/10 border border-red-500/30"
                                                : "bg-yellow-500/10 border border-yellow-500/30"
                                    )}>
                                        {selectedTransfer.is_verified ? (
                                            <>
                                                <CheckCircle2 size={32} className="mx-auto mb-2 text-green-500" />
                                                <div className="font-medium text-green-500">Verified</div>
                                                <div className="text-xs text-muted mt-1 font-mono">
                                                    {selectedTransfer.verification_hash?.slice(0, 16)}...
                                                </div>
                                            </>
                                        ) : selectedTransfer.has_discrepancy ? (
                                            <>
                                                <XCircle size={32} className="mx-auto mb-2 text-red-500" />
                                                <div className="font-medium text-red-500">Disputed</div>
                                                <div className="text-xs text-muted mt-1">
                                                    {selectedTransfer.discrepancy_type}
                                                </div>
                                            </>
                                        ) : (
                                            <>
                                                <Clock size={32} className="mx-auto mb-2 text-yellow-500" />
                                                <div className="font-medium text-yellow-500">Pending Verification</div>
                                            </>
                                        )}
                                    </div>

                                    {/* Chain Steps */}
                                    <div className="space-y-4">
                                        <ChainStep
                                            step={1}
                                            label="Sender"
                                            party={selectedTransfer.created_by}
                                            timestamp={selectedTransfer.created_at}
                                            signature={selectedTransfer.sender_signature}
                                            completed={!!selectedTransfer.sender_signature}
                                        />
                                        <ChainStep
                                            step={2}
                                            label="Transporter"
                                            party={selectedTransfer.transporter_id}
                                            timestamp={selectedTransfer.pickup_at}
                                            signature={selectedTransfer.transporter_signature}
                                            completed={!!selectedTransfer.transporter_signature}
                                        />
                                        <ChainStep
                                            step={3}
                                            label="Receiver"
                                            party={selectedTransfer.receiver_id}
                                            timestamp={selectedTransfer.delivered_at}
                                            signature={selectedTransfer.receiver_signature}
                                            completed={!!selectedTransfer.receiver_signature}
                                        />
                                    </div>

                                    {/* Quantity Check */}
                                    {selectedTransfer.received_quantity !== null && (
                                        <div className="p-3 bg-[var(--bg-elevated)] rounded-lg">
                                            <div className="text-xs text-muted mb-2">Quantity Verification</div>
                                            <div className="flex justify-between items-center">
                                                <span className="text-sm">Sent</span>
                                                <span className="font-mono">{selectedTransfer.quantity}</span>
                                            </div>
                                            <div className="flex justify-between items-center">
                                                <span className="text-sm">Received</span>
                                                <span className={cn(
                                                    "font-mono",
                                                    selectedTransfer.received_quantity !== selectedTransfer.quantity && "text-critical"
                                                )}>
                                                    {selectedTransfer.received_quantity}
                                                </span>
                                            </div>
                                            {selectedTransfer.received_quantity !== selectedTransfer.quantity && (
                                                <div className="flex justify-between items-center text-critical">
                                                    <span className="text-sm">Missing</span>
                                                    <span className="font-mono font-bold">
                                                        {selectedTransfer.quantity - selectedTransfer.received_quantity}
                                                    </span>
                                                </div>
                                            )}
                                        </div>
                                    )}
                                </div>
                            ) : (
                                <div className="text-center py-12">
                                    <Shield size={32} className="mx-auto mb-3 text-muted opacity-40" />
                                    <p className="text-secondary">Select a transfer to view details</p>
                                </div>
                            )}
                        </PanelBody>
                    </Panel>
                </div>
            </div>

            {/* Create Transfer Modal */}
            {showCreateForm && (
                <CreateTransferModal
                    onClose={() => setShowCreateForm(false)}
                    onSuccess={() => {
                        setShowCreateForm(false);
                        loadData();
                    }}
                />
            )}
        </div>
    );
}

/* ===== CREATE TRANSFER MODAL ===== */

function CreateTransferModal({
    onClose,
    onSuccess
}: {
    onClose: () => void;
    onSuccess: () => void;
}) {
    const [formData, setFormData] = useState({
        from_district_id: "RJ-JP",
        to_district_id: "RJ-UD",
        medicine_id: "PARA-500",
        quantity: 500,
        priority: "normal",
        created_by: "CMO-USER"
    });
    const [submitting, setSubmitting] = useState(false);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (formData.from_district_id === formData.to_district_id) {
            alert("Source and destination must be different!");
            return;
        }

        setSubmitting(true);
        try {
            await createTransfer(formData);
            onSuccess();
        } catch (error) {
            console.error("Error creating transfer:", error);
            alert("Error creating transfer");
        } finally {
            setSubmitting(false);
        }
    };

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
            <div className="bg-[var(--bg-elevated)] rounded-xl border border-[var(--border)] w-full max-w-md mx-4 shadow-2xl">
                {/* Header */}
                <div className="flex items-center justify-between p-4 border-b border-[var(--border)]">
                    <div className="flex items-center gap-2">
                        <Plus size={18} className="text-green-500" />
                        <span className="font-semibold">Create Transfer</span>
                    </div>
                    <button
                        onClick={onClose}
                        className="p-1 hover:bg-[var(--bg-base)] rounded transition-colors"
                    >
                        <X size={18} />
                    </button>
                </div>

                {/* Form */}
                <form onSubmit={handleSubmit} className="p-4 space-y-4">
                    {/* From District */}
                    <div>
                        <label className="block text-xs text-muted mb-1.5">From District</label>
                        <select
                            value={formData.from_district_id}
                            onChange={(e) => setFormData({ ...formData, from_district_id: e.target.value })}
                            className="w-full px-3 py-2 bg-[var(--bg-base)] border border-[var(--border)] rounded-lg text-sm focus:outline-none focus:border-accent"
                        >
                            {DISTRICTS.map((d) => (
                                <option key={d.id} value={d.id}>{d.name} ({d.id})</option>
                            ))}
                        </select>
                    </div>

                    {/* To District */}
                    <div>
                        <label className="block text-xs text-muted mb-1.5">To District</label>
                        <select
                            value={formData.to_district_id}
                            onChange={(e) => setFormData({ ...formData, to_district_id: e.target.value })}
                            className="w-full px-3 py-2 bg-[var(--bg-base)] border border-[var(--border)] rounded-lg text-sm focus:outline-none focus:border-accent"
                        >
                            {DISTRICTS.map((d) => (
                                <option key={d.id} value={d.id}>{d.name} ({d.id})</option>
                            ))}
                        </select>
                    </div>

                    {/* Medicine */}
                    <div>
                        <label className="block text-xs text-muted mb-1.5">Medicine</label>
                        <select
                            value={formData.medicine_id}
                            onChange={(e) => setFormData({ ...formData, medicine_id: e.target.value })}
                            className="w-full px-3 py-2 bg-[var(--bg-base)] border border-[var(--border)] rounded-lg text-sm focus:outline-none focus:border-accent"
                        >
                            {MEDICINES.map((m) => (
                                <option key={m.id} value={m.id}>{m.name}</option>
                            ))}
                        </select>
                    </div>

                    {/* Quantity */}
                    <div>
                        <label className="block text-xs text-muted mb-1.5">Quantity</label>
                        <input
                            type="number"
                            value={formData.quantity}
                            onChange={(e) => setFormData({ ...formData, quantity: parseInt(e.target.value) || 0 })}
                            min={1}
                            max={10000}
                            className="w-full px-3 py-2 bg-[var(--bg-base)] border border-[var(--border)] rounded-lg text-sm focus:outline-none focus:border-accent"
                        />
                    </div>

                    {/* Priority */}
                    <div>
                        <label className="block text-xs text-muted mb-1.5">Priority</label>
                        <div className="flex gap-2">
                            {["normal", "urgent", "critical"].map((p) => (
                                <button
                                    key={p}
                                    type="button"
                                    onClick={() => setFormData({ ...formData, priority: p })}
                                    className={cn(
                                        "flex-1 py-2 px-3 rounded-lg text-sm font-medium transition-colors",
                                        formData.priority === p
                                            ? p === "critical"
                                                ? "bg-red-500/20 text-red-500 border border-red-500/50"
                                                : p === "urgent"
                                                    ? "bg-orange-500/20 text-orange-500 border border-orange-500/50"
                                                    : "bg-[var(--accent)]/20 text-accent border border-accent/50"
                                            : "bg-[var(--bg-base)] text-secondary border border-[var(--border)] hover:border-[var(--border-accent)]"
                                    )}
                                >
                                    {p.charAt(0).toUpperCase() + p.slice(1)}
                                </button>
                            ))}
                        </div>
                    </div>

                    {/* Officer ID */}
                    <div>
                        <label className="block text-xs text-muted mb-1.5">Your Officer ID</label>
                        <input
                            type="text"
                            value={formData.created_by}
                            onChange={(e) => setFormData({ ...formData, created_by: e.target.value })}
                            placeholder="e.g. CMO-JAIPUR"
                            className="w-full px-3 py-2 bg-[var(--bg-base)] border border-[var(--border)] rounded-lg text-sm focus:outline-none focus:border-accent"
                        />
                    </div>

                    {/* Submit */}
                    <div className="flex gap-3 pt-2">
                        <Button
                            type="button"
                            variant="ghost"
                            className="flex-1"
                            onClick={onClose}
                        >
                            Cancel
                        </Button>
                        <Button
                            type="submit"
                            disabled={submitting}
                            className="flex-1 bg-green-600 hover:bg-green-700 text-white"
                        >
                            {submitting ? (
                                <RefreshCw size={14} className="animate-spin mr-2" />
                            ) : (
                                <Plus size={14} className="mr-2" />
                            )}
                            Create Transfer
                        </Button>
                    </div>
                </form>
            </div>
        </div>
    );
}

/* ===== COMPONENTS ===== */

function StatusCard({
    icon,
    label,
    value,
    color
}: {
    icon: React.ReactNode;
    label: string;
    value: number;
    color: 'success' | 'warning' | 'critical' | 'default';
}) {
    const colorClasses = {
        success: 'text-green-500',
        warning: 'text-yellow-500',
        critical: 'text-red-500',
        default: 'text-primary'
    };

    return (
        <div className="metric-card">
            <div className="flex items-center gap-2 mb-2">
                <span className={colorClasses[color]}>{icon}</span>
                <span className="text-xs text-muted uppercase tracking-wide">{label}</span>
            </div>
            <div className={cn("text-3xl font-bold font-mono", colorClasses[color])}>
                {value}
            </div>
        </div>
    );
}

function StatusBadge({ status }: { status: string }) {
    const config: Record<string, { label: string; class: string }> = {
        created: { label: 'Created', class: 'bg-gray-500/20 text-gray-400' },
        picked_up: { label: 'In Transit', class: 'bg-yellow-500/20 text-yellow-500' },
        delivered: { label: 'Delivered', class: 'bg-blue-500/20 text-blue-500' },
        verified: { label: 'Verified', class: 'bg-green-500/20 text-green-500' },
        disputed: { label: 'Disputed', class: 'bg-red-500/20 text-red-500' }
    };

    const { label, class: className } = config[status] || config.created;

    return (
        <span className={cn("px-2 py-0.5 rounded text-xs font-medium", className)}>
            {label}
        </span>
    );
}

function PriorityBadge({ priority }: { priority: string }) {
    if (priority === 'normal') return null;

    const config: Record<string, { label: string; class: string }> = {
        urgent: { label: 'URGENT', class: 'bg-orange-500/20 text-orange-500' },
        critical: { label: 'CRITICAL', class: 'bg-red-500/20 text-red-500' }
    };

    const { label, class: className } = config[priority] || { label: priority, class: '' };

    return (
        <span className={cn("px-2 py-0.5 rounded text-[10px] font-bold uppercase", className)}>
            {label}
        </span>
    );
}

function ChainStep({
    step,
    label,
    party,
    timestamp,
    signature,
    completed
}: {
    step: number;
    label: string;
    party: string | null;
    timestamp: string | null;
    signature: string | null;
    completed: boolean;
}) {
    return (
        <div className={cn(
            "flex gap-3 p-3 rounded-lg border",
            completed
                ? "border-green-500/30 bg-green-500/5"
                : "border-[var(--border)] bg-[var(--bg-elevated)]"
        )}>
            <div className={cn(
                "w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold flex-shrink-0",
                completed ? "bg-green-500 text-white" : "bg-[var(--border)] text-muted"
            )}>
                {completed ? <CheckCircle2 size={16} /> : step}
            </div>
            <div className="flex-1 min-w-0">
                <div className="flex justify-between items-center">
                    <span className="font-medium text-sm">{label}</span>
                    {completed && <CheckCircle2 size={14} className="text-green-500" />}
                </div>
                {party && (
                    <div className="text-xs text-secondary mt-1">{party}</div>
                )}
                {timestamp && (
                    <div className="text-xs text-muted mt-1">
                        {new Date(timestamp).toLocaleString()}
                    </div>
                )}
                {signature && (
                    <div className="text-[10px] font-mono text-muted mt-1 truncate">
                        Sig: {signature.slice(0, 16)}...
                    </div>
                )}
            </div>
        </div>
    );
}
