import type { ReactNode } from "react";

import { AppHeader, type AppNavItem } from "./app-header";
import type { AppUser } from "./user-profile-menu";

type AppShellProps<TMode extends string = string> = {
  appName: string;
  brandPrefix?: string;
  brandLogoSrc?: string;
  subtitle?: string;
  navItems?: Array<AppNavItem<TMode>>;
  activeItem?: TMode;
  onSelectItem?: (id: TMode) => void;
  navPrefixAccessory?: ReactNode;
  user?: AppUser;
  footer?: ReactNode;
  rightAccessory?: ReactNode;
  children: ReactNode;
};

export function AppShell<TMode extends string = string>({
  appName,
  brandPrefix,
  brandLogoSrc,
  subtitle,
  navItems,
  activeItem,
  onSelectItem,
  navPrefixAccessory,
  user,
  footer,
  rightAccessory,
  children,
}: AppShellProps<TMode>) {
  return (
    <div className="relative flex min-h-screen flex-col overflow-hidden bg-eyp-bg">
      <div className="fixed inset-0 z-0 pointer-events-none">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_left,rgba(26,154,250,0.12),transparent_32rem),radial-gradient(circle_at_bottom_right,rgba(14,165,233,0.09),transparent_30rem),linear-gradient(180deg,hsl(var(--eyp-bg))_0%,hsl(var(--background))_48%,hsl(var(--eyp-bg))_100%)]" />
      </div>

      <div className="relative z-10 flex min-h-screen flex-col">
        <AppHeader
          appName={appName}
          brandPrefix={brandPrefix}
          brandLogoSrc={brandLogoSrc}
          subtitle={subtitle}
          navItems={navItems}
          activeItem={activeItem}
          onSelectItem={onSelectItem}
          navPrefixAccessory={navPrefixAccessory}
          user={user}
          rightAccessory={rightAccessory}
        />

        <main className="container mx-auto flex-1 px-4 py-6">{children}</main>

        <footer className="border-t border-border/60 bg-eyp-bg-light/60 backdrop-blur">
          <div className="container mx-auto flex flex-col gap-1 px-4 py-4 text-xs text-muted-foreground sm:flex-row sm:items-center sm:justify-between">
            {footer ?? (
              <>
                <span>EW app starter</span>
                <span>Theme, profile, shell, and section styles ready to reuse</span>
              </>
            )}
          </div>
        </footer>
      </div>
    </div>
  );
}
