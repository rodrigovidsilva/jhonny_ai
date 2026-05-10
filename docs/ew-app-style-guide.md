# EW App Starter And Style Guide

**Status:** Current starter reference
**Audience:** App builders using the EW/EY-P app shell  
**Scope:** Reusable frontend structure, theme behavior, profile menu, and section styling

---

## Table Of Contents

1. [Purpose](#1-purpose)
2. [Starter Structure](#2-starter-structure)
3. [Theme And Tokens](#3-theme-and-tokens)
4. [Shell, Header, And Profile](#4-shell-header-and-profile)
5. [Section And Card Patterns](#5-section-and-card-patterns)
6. [New App Checklist](#6-new-app-checklist)

## 1. Purpose

This starter preserves the structure and visual style of the EW Use Case Hub for future apps. It keeps the same top-right dark/light toggle, profile button/dropdown, EY-P blue highlights, Aptos/Inter/Segoe UI font stack, card borders, and dark-first app frame.

The reusable implementation lives in `frontend/components/app-shell` and is designed for Next.js apps, while the same classes and tokens can be copied into other React/Tailwind projects. The current Jhonny app also uses optional brand logo and navigation accessory slots for client-specific controls such as the demo token input.

## 2. Starter Structure

Core files:

| File | Use |
| --- | --- |
| `frontend/tailwind.config.ts` | Tailwind dark mode, color tokens, fonts, animations, and EY-P palette. |
| `frontend/app/globals.css` | Light/dark CSS variables, base typography, scrollbars, `.glass`, and `.gradient-text`. |
| `frontend/components/app-shell/theme-provider.tsx` | Theme context, persisted mode, document `.dark` class, and theme-color metadata. |
| `frontend/components/app-shell/app-shell.tsx` | Sticky header, centered main content, footer, and app background. |
| `frontend/components/app-shell/app-header.tsx` | Brand, navigation, profile button, and dark/light toggle. |
| `frontend/components/app-shell/user-profile-menu.tsx` | Avatar trigger, profile dropdown, and edit-profile dialog. |
| `frontend/components/app-shell/section-card.tsx` | Section border/highlight classes and `SectionCard`. |
| `frontend/components/ui/*` | Minimal shadcn-style primitives used by the starter. |

## 3. Theme And Tokens

Use class-based dark mode. The active mode is stored in `localStorage` under `ew-app-theme`, and the `ThemeProvider` applies or removes the `dark` class on `<html>`.

Use the shared app wrapper in `frontend/app/layout.tsx`:

```tsx
<html lang="en" className="dark" suppressHydrationWarning>
  <body>
    <ThemeProvider>{children}</ThemeProvider>
  </body>
</html>
```

The key Tailwind tokens are:

| Token | Purpose |
| --- | --- |
| `eyp-blue` | Primary accent and active navigation color. |
| `eyp-bg` | Full-page app background. |
| `eyp-bg-light` | Header, popover, and panel backgrounds. |
| `background`, `foreground`, `card`, `border`, `ring` | Semantic shadcn-compatible colors. |

Keep the font stack as:

```ts
["Aptos", "Inter", "Segoe UI", "ui-sans-serif", "system-ui", "sans-serif"]
```

## 4. Shell, Header, And Profile

Wrap each app page in `AppShell`:

```tsx
<AppShell
  appName="My App"
  brandPrefix="EW"
  brandLogoSrc="/optional-logo.png"
  subtitle="AI-enabled workflow"
  navItems={navItems}
  activeItem={mode}
  onSelectItem={setMode}
  navPrefixAccessory={optionalNavControl}
  rightAccessory={optionalHeaderControl}
  user={user}
  footer={<span>Client-facing footer text</span>}
>
  {children}
</AppShell>
```

The header keeps the same structure as the Use Case Hub:

| Area | Behavior |
| --- | --- |
| Left brand | Optional image logo, or two-letter mark, blue prefix, app name, and optional subtitle. |
| Navigation | Horizontally scrollable ghost buttons with optional icons and hover blue treatment. |
| Navigation accessory | Optional `navPrefixAccessory` slot before nav items, useful for compact controls like a demo token input. |
| Right accessory | Optional `rightAccessory` slot before profile/theme controls. |
| Profile | Rounded avatar button, right-aligned dropdown, edit dialog. |
| Theme | Top-right icon button using `Moon` and `Sun`; toggles light/dark. |

The profile menu is prop-driven. Future apps can wire `onSaveProfile` to their own API without changing the UI pattern.

## 5. Section And Card Patterns

Use `SectionCard` for major page sections:

```tsx
<SectionCard title="Analytics dashboard" description="Live operational view">
  <div className={fieldGroupClass}>...</div>
</SectionCard>
```

Shared section classes:

| Class | Use |
| --- | --- |
| `sectionCardClass` | Blue-tinted border, gradient background, soft blue shadow. |
| `sectionHeaderClass` | Blue-tinted header band and separator. |
| `fieldGroupClass` | Spacious rounded field/panel blocks. |
| `compactFieldGroupClass` | Smaller repeated rows, history items, and chart rows. |
| `fieldLabelClass` | Small uppercase labels with dark-mode blue accent. |
| `nestedPanelClass` | Secondary nested panels inside a card. |

Prefer semantic colors and tokens over hard-coded colors. Use `bg-eyp-blue/10`, `border-eyp-blue/10`, `text-muted-foreground`, `bg-card`, and `bg-background/40` for consistent light/dark behavior.

## 6. New App Checklist

1. Copy or keep `tailwind.config.ts`, `app/globals.css`, `lib/utils.ts`, `components/ui`, and `components/app-shell`.
2. Wrap the app with `ThemeProvider` in the root layout.
3. Use `AppShell` for every main page.
4. Put `UserProfileMenu` and the dark/light toggle in the top-right header through `AppHeader`.
5. Build page regions with `SectionCard`, `fieldGroupClass`, and `compactFieldGroupClass`.
6. Use `brandLogoSrc`, `navPrefixAccessory`, or `rightAccessory` only when the app needs client branding or compact header controls.
7. Keep navigation hover and selected treatments consistent with the current shell.
8. Verify both themes before shipping: page background, cards, borders, forms, popovers, and dialogs.
