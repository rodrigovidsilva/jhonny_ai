import type { ReactNode } from "react";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { cn } from "@/lib/utils";

export const sectionCardClass =
  "overflow-hidden border border-eyp-blue/25 bg-gradient-to-br from-eyp-blue/10 via-card/95 to-card/95 shadow-[0_22px_70px_-46px_rgba(26,154,250,0.62)] outline outline-1 outline-white/5 backdrop-blur-sm dark:border-eyp-blue/20 dark:from-eyp-blue/8";
export const sectionHeaderClass = "border-b border-eyp-blue/15 bg-eyp-blue/5";
export const fieldGroupClass = "space-y-2 rounded-2xl border border-eyp-blue/15 bg-background/45 p-4 shadow-inner shadow-eyp-blue/5";
export const compactFieldGroupClass =
  "space-y-1.5 rounded-xl border border-eyp-blue/15 bg-background/45 p-3 shadow-inner shadow-eyp-blue/5";
export const fieldLabelClass =
  "text-[11px] font-semibold uppercase tracking-[0.18em] text-foreground/90 dark:text-eyp-blue";
export const nestedPanelClass = "rounded-xl border border-eyp-blue/15 bg-background/40 p-3";
export const overviewValueBadgeClass = "min-h-10 rounded-xl px-4 py-2 text-sm font-semibold shadow-sm";
export const sectionContentClass = "pt-4";

type SectionCardProps = {
  title?: ReactNode;
  description?: ReactNode;
  action?: ReactNode;
  children: ReactNode;
  className?: string;
  contentClassName?: string;
};

export function SectionCard({
  title,
  description,
  action,
  children,
  className,
  contentClassName,
}: SectionCardProps) {
  return (
    <Card className={cn(sectionCardClass, className)}>
      {(title || description || action) && (
        <CardHeader className={cn(sectionHeaderClass, "flex-row items-start justify-between gap-4 space-y-0")}>
          <div className="space-y-1.5">
            {title && <CardTitle>{title}</CardTitle>}
            {description && <CardDescription>{description}</CardDescription>}
          </div>
          {action}
        </CardHeader>
      )}
      <CardContent className={cn(title || description || action ? sectionContentClass : "pt-6", contentClassName)}>
        {children}
      </CardContent>
    </Card>
  );
}
