"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
    LayoutGrid,
    MapPin,
    AlertTriangle,
    Sliders,
    Activity,
    Shield,
} from "lucide-react";
import { cn } from "@/lib/utils";

const navItems = [
    { href: "/", label: "Command Center", icon: LayoutGrid },
    { href: "/district/RJ-JP", label: "District Analysis", icon: MapPin },
    { href: "/alerts", label: "Threat Detection", icon: AlertTriangle },
    { href: "/simulator", label: "Scenario Engine", icon: Sliders },
    { href: "/transfers", label: "Transfer Verification", icon: Shield },
];

export default function Sidebar() {
    const pathname = usePathname();

    return (
        <aside className="app-sidebar">
            {/* Logo */}
            <div className="sidebar-logo">
                <div className="sidebar-logo-icon">
                    <Activity size={18} />
                </div>
                <div>
                    <div className="sidebar-logo-text">MedPredict</div>
                    <div className="sidebar-logo-sub">AI Platform</div>
                </div>
            </div>

            {/* Navigation */}
            <nav className="flex-1 py-4">
                <div className="sidebar-section">Operations</div>
                {navItems.map((item) => {
                    const isActive = pathname === item.href ||
                        (item.href !== "/" && pathname.startsWith(item.href.split("/")[1] ? `/${item.href.split("/")[1]}` : item.href));

                    return (
                        <Link
                            key={item.href}
                            href={item.href}
                            className={cn("sidebar-link", isActive && "active")}
                        >
                            <item.icon size={18} />
                            {item.label}
                        </Link>
                    );
                })}
            </nav>

            {/* Footer */}
            <div className="sidebar-footer">
                <div className="flex items-center gap-2 text-sm">
                    <span className="status-dot status-success" />
                    <span className="text-muted">Systems Online</span>
                </div>
                <div className="text-xs text-muted mt-1">
                    Rajasthan Health Network
                </div>
            </div>
        </aside>
    );
}
