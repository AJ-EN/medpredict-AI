import { cn } from "@/lib/utils";
import { ReactNode } from "react";
import {
    Card,
    CardHeader,
    CardTitle,
    CardContent,
} from "@/components/ui/card";

interface PanelProps {
    children: ReactNode;
    className?: string;
}

interface PanelHeaderProps {
    children: ReactNode;
    className?: string;
    actions?: ReactNode;
}

interface PanelBodyProps {
    children: ReactNode;
    className?: string;
    noPadding?: boolean;
}

/**
 * Clean Panel component for content sections.
 * Calm, professional appearance with generous spacing.
 */
export function Panel({ children, className }: PanelProps) {
    return (
        <Card className={cn("border-border shadow-none bg-card", className)}>
            {children}
        </Card>
    );
}

export function PanelHeader({ children, className, actions }: PanelHeaderProps) {
    return (
        <CardHeader className={cn("flex flex-row items-center justify-between border-b border-border py-4 px-6 space-y-0", className)}>
            <CardTitle className="text-[13px] font-semibold uppercase tracking-wider text-secondary-foreground">{children}</CardTitle>
            {actions && <div className="flex items-center gap-3">{actions}</div>}
        </CardHeader>
    );
}

export function PanelBody({ children, className, noPadding = false }: PanelBodyProps) {
    return (
        <CardContent className={cn("p-6", noPadding && "p-0", className)}>
            {children}
        </CardContent>
    );
}
