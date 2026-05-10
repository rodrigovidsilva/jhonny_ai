"use client";

import type { ReactNode } from "react";
import { Moon, Sun, type LucideIcon } from "lucide-react";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

import { useDocumentIsDarkMode, useTheme } from "./theme-provider";
import { AppUser, UserProfileMenu } from "./user-profile-menu";

export type AppNavItem<TMode extends string = string> = {
  id: TMode;
  label: string;
  icon?: LucideIcon;
};

type AppHeaderProps<TMode extends string = string> = {
  appName: string;
  brandPrefix?: string;
  brandLogoSrc?: string;
  subtitle?: string;
  navItems?: Array<AppNavItem<TMode>>;
  activeItem?: TMode;
  onSelectItem?: (id: TMode) => void;
  navPrefixAccessory?: ReactNode;
  user?: AppUser;
  rightAccessory?: ReactNode;
};

export function AppHeader<TMode extends string = string>({
  appName,
  brandPrefix = "EW",
  brandLogoSrc,
  subtitle,
  navItems = [],
  activeItem: _activeItem,
  onSelectItem,
  navPrefixAccessory,
  user,
  rightAccessory,
}: AppHeaderProps<TMode>) {
  const { toggleTheme } = useTheme();
  const isDarkMode = useDocumentIsDarkMode();

  return (
    <header className="sticky top-0 z-40 border-b border-border/80 bg-eyp-bg/85 backdrop-blur-xl supports-[backdrop-filter]:bg-eyp-bg/65">
      <div className="container mx-auto px-4">
        <div className="flex min-h-16 items-center justify-between gap-4 py-2">
          <div className="flex min-w-0 shrink-0 items-center gap-2.5">
            {brandLogoSrc ? (
              <div className="grid h-11 w-11 shrink-0 place-items-center overflow-hidden rounded-xl border border-eyp-blue/25 bg-white p-1.5 shadow-[0_18px_36px_-26px_rgba(26,154,250,0.8)]">
                <img src={brandLogoSrc} alt={`${appName} logo`} className="h-full w-full object-contain" />
              </div>
            ) : (
              <div className="grid h-10 w-10 shrink-0 place-items-center rounded-xl border border-eyp-blue/25 bg-eyp-blue/10 text-sm font-black text-eyp-blue shadow-[0_18px_36px_-26px_rgba(26,154,250,0.8)]">
                {brandPrefix.slice(0, 2).toUpperCase()}
              </div>
            )}
            <div className="min-w-0">
              <div className="truncate text-base font-semibold">
                <span className="text-eyp-blue">{brandPrefix}</span> {appName}
              </div>
              {subtitle && <div className="truncate text-xs text-muted-foreground">{subtitle}</div>}
            </div>
          </div>

          <div className="flex min-w-0 flex-1 items-center justify-end gap-2">
            {navItems.length > 0 && (
              <div className="min-w-0 flex-1 overflow-x-auto">
                <nav className="flex min-w-max items-center justify-end gap-1 py-1" aria-label="Main navigation">
                  {navPrefixAccessory}
                  {navItems.map((item) => {
                    const Icon = item.icon;

                    return (
                      <button
                        key={item.id}
                        type="button"
                        onClick={() => onSelectItem?.(item.id)}
                        className="inline-flex h-8 items-center justify-center gap-2 whitespace-nowrap rounded-md border border-transparent !bg-transparent px-3 text-xs font-medium text-muted-foreground !shadow-none transition-colors hover:border-eyp-blue/30 hover:!bg-eyp-blue/10 hover:text-eyp-blue focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
                      >
                        {Icon && <Icon className="h-4 w-4" />}
                        <span className="hidden lg:inline">{item.label}</span>
                      </button>
                    );
                  })}
                </nav>
              </div>
            )}

            {rightAccessory}

            {user && (
              <div className="flex shrink-0 items-center border-l border-border/60 pl-2">
                <UserProfileMenu user={user} />
              </div>
            )}

            <div className="flex shrink-0 items-center gap-0.5">
              <button
                type="button"
                className="inline-flex h-10 w-10 items-center justify-center rounded-full border border-transparent !bg-transparent text-muted-foreground !shadow-none transition-colors hover:border-border/70 hover:!bg-background/50 hover:text-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
                onClick={toggleTheme}
                aria-label={isDarkMode ? "Switch to light mode" : "Switch to dark mode"}
                title={isDarkMode ? "Switch to light mode" : "Switch to dark mode"}
              >
                {isDarkMode ? <Moon className="h-5 w-5" aria-hidden /> : <Sun className="h-5 w-5" aria-hidden />}
              </button>
            </div>
          </div>
        </div>
      </div>
    </header>
  );
}
