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
    XCircle
} from "lucide-react";
import { Panel, PanelHeader, PanelBody } from "@/components/ui/Panel";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { getTransfers, getAnomalousTransfers, type Transfer } from "@/lib/api";

interface TransferWithAnomalies {
    transfer: Transfer;
    anomalies: Array<{ type: string; severity: string; message: string }>;
}

export default function TransfersDashboard() {
    const [transfers, setTransfers] = useState<Transfer[]>([]);
    const [anomalies, setAnomalies] = useState<TransferWithAnomalies[]>([]);
    const [statusCounts, setStatusCounts] = useState<Record<string, number>>({});
    const [loading, setLoading] = useState(true);
    const [selectedTransfer, setSelectedTransfer] = useState<Transfer | null>(null);

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
                    <div className="flex items-center gap-2">
                        <Clock size={14} />
                        <span>{new Date().toLocaleTimeString()}</span>
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
                                        <p className="text-sm text-muted mt-1">Transfers will appear here when created</p>
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
