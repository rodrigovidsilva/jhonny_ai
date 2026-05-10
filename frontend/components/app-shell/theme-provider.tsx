"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  useSyncExternalStore,
  type ReactNode,
} from "react";

const STORAGE_KEY = "ew-app-theme";

export type ThemeMode = "light" | "dark";

type ThemeContextValue = {
  theme: ThemeMode;
  setTheme: (mode: ThemeMode) => void;
  toggleTheme: () => void;
};

const ThemeContext = createContext<ThemeContextValue | null>(null);

function applyThemeToDocument(mode: ThemeMode) {
  const root = document.documentElement;
  root.classList.toggle("dark", mode === "dark");

  const meta = document.querySelector('meta[name="theme-color"]');
  if (meta) {
    meta.setAttribute("content", mode === "dark" ? "#1a1a24" : "#f7f8fc");
  }

  try {
    localStorage.setItem(STORAGE_KEY, mode);
  } catch {
    /* ignore unavailable storage */
  }
}

export function getStoredTheme(): ThemeMode {
  if (typeof window === "undefined") return "dark";

  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw === "light" || raw === "dark") return raw;
  } catch {
    /* ignore unavailable storage */
  }

  return "dark";
}

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [theme, setThemeState] = useState<ThemeMode>(() => getStoredTheme());

  useEffect(() => {
    applyThemeToDocument(theme);
  }, [theme]);

  const setTheme = useCallback((mode: ThemeMode) => {
    setThemeState(mode);
  }, []);

  const toggleTheme = useCallback(() => {
    setThemeState((current) => (current === "dark" ? "light" : "dark"));
  }, []);

  const value = useMemo(
    () => ({ theme, setTheme, toggleTheme }),
    [theme, setTheme, toggleTheme]
  );

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
}

export function useTheme() {
  const ctx = useContext(ThemeContext);
  if (!ctx) {
    throw new Error("useTheme must be used within ThemeProvider");
  }
  return ctx;
}

export function useDocumentIsDarkMode(): boolean {
  return useSyncExternalStore(
    (onStoreChange) => {
      const el = document.documentElement;
      const observer = new MutationObserver(() => onStoreChange());
      observer.observe(el, { attributes: true, attributeFilter: ["class"] });
      window.addEventListener("storage", onStoreChange);
      return () => {
        observer.disconnect();
        window.removeEventListener("storage", onStoreChange);
      };
    },
    () => document.documentElement.classList.contains("dark"),
    () => true
  );
}
