"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
    LayoutDashboard,
    MapPin,
    Bell,
    PlayCircle,
    Package,
    Activity
} from "lucide-react";

const navItems = [
    { href: "/", label: "State Overview", icon: LayoutDashboard },
    { href: "/district/RJ-JD", label: "District View", icon: MapPin },
    { href: "/alerts", label: "Early Warning", icon: Bell },
    { href: "/simulator", label: "Scenario Simulator", icon: PlayCircle },
];

export default function Sidebar() {
    const pathname = usePathname();

    return (
        <aside className="sidebar">
            {/* Logo */}
            <div style={{ padding: "24px 20px", borderBottom: "1px solid var(--border)" }}>
                <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
                    <div style={{
                        width: 40,
                        height: 40,
                        borderRadius: 10,
                        background: "linear-gradient(135deg, #3b82f6 0%, #8b5cf6 100%)",
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center"
                    }}>
                        <Activity size={24} color="white" />
                    </div>
                    <div>
                        <h1 style={{ fontSize: 18, fontWeight: 700, letterSpacing: "-0.5px" }}>MedPredict AI</h1>
                        <p style={{ fontSize: 11, color: "var(--muted)", marginTop: 2 }}>Rajasthan Health Ministry</p>
                    </div>
                </div>
            </div>

            {/* Navigation */}
            <nav style={{ padding: "16px 0" }}>
                <p style={{
                    fontSize: 11,
                    color: "var(--muted)",
                    padding: "8px 20px",
                    textTransform: "uppercase",
                    letterSpacing: "1px"
                }}>
                    Dashboard
                </p>
                {navItems.map((item) => {
                    const isActive = pathname === item.href ||
                        (item.href !== "/" && pathname.startsWith(item.href.split("/")[1] ? `/${item.href.split("/")[1]}` : item.href));

                    return (
                        <Link
                            key={item.href}
                            href={item.href}
                            className={`sidebar-link ${isActive ? "active" : ""}`}
                        >
                            <item.icon size={20} />
                            {item.label}
                        </Link>
                    );
                })}
            </nav>

            {/* Status indicator */}
            <div style={{
                position: "absolute",
                bottom: 0,
                left: 0,
                right: 0,
                padding: "16px 20px",
                borderTop: "1px solid var(--border)",
                background: "rgba(10, 10, 15, 0.9)"
            }}>
                <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                    <div style={{
                        width: 8,
                        height: 8,
                        borderRadius: "50%",
                        background: "#22c55e",
                        boxShadow: "0 0 8px rgba(34, 197, 94, 0.5)"
                    }} />
                    <span style={{ fontSize: 12, color: "var(--muted)" }}>System Operational</span>
                </div>
                <p style={{ fontSize: 11, color: "var(--muted)", marginTop: 4 }}>
                    Last updated: {new Date().toLocaleTimeString()}
                </p>
            </div>
        </aside>
    );
}
