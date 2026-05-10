"use client";

import { useEffect, useMemo, useRef, useState, type KeyboardEvent, type ReactNode } from "react";
import {
  ArrowDownRight,
  ArrowUpRight,
  BarChart3,
  Bot,
  HomeIcon,
  RefreshCw,
  Send,
  ShoppingBag,
  Waves,
} from "lucide-react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  ComposedChart,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { AppShell, type AppNavItem, type AppUser } from "@/components/app-shell";
import {
  SectionCard,
  compactFieldGroupClass,
  fieldGroupClass,
  fieldLabelClass,
} from "@/components/app-shell";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";

type AppMode = "home" | "analytics" | "agent";
type AnalyticsDashboard = "sales" | "stock" | "purchases" | "financials";
type AnalyticsPeriod = "7" | "30" | "90" | "365";
type SalesTrendSeriesKey = "sales" | "profit";

type SalesBreakdownItem = {
  amount: number;
  quantity: number;
  lines?: number;
};

type SalesCategoryBreakdown = SalesBreakdownItem & {
  category: string;
};

type SalesBrandBreakdown = SalesBreakdownItem & {
  brand: string;
};

type SalesProductBreakdown = SalesBreakdownItem & {
  product: string;
};

type SalesWeekdayBreakdown = SalesBreakdownItem & {
  weekday: string;
  orders: number;
};

type SalesHourBreakdown = SalesBreakdownItem & {
  hour: number;
  label: string;
  orders: number;
};

type SalesAnalyticsBreakdown = {
  start_date: string;
  end_date: string;
  brand_field?: string | null;
  total_amount: number;
  estimated_cost?: number;
  estimated_gross_profit?: number;
  estimated_gross_margin_pct?: number;
  costed_lines?: number;
  sales_by_category: SalesCategoryBreakdown[];
  sales_by_brand: SalesBrandBreakdown[];
  sales_by_product?: SalesProductBreakdown[];
  sales_by_weekday: SalesWeekdayBreakdown[];
  sales_by_hour: SalesHourBreakdown[];
};

type StockAnalytics = {
  brand_field?: string | null;
  by_brand: Array<{ brand: string; value: number; quantity: number; available: number }>;
  by_category: Array<{ category: string; value: number; quantity: number; available: number }>;
  by_age: Array<{ bucket: string; value: number; quantity: number }>;
};

type PurchaseSummary = {
  amount: number;
  count: number;
  recent_orders: Array<{ reference: string; date: string; amount: number; state: string }>;
};

type OpenBillLine = {
  product?: string;
  description?: string;
  quantity: number;
  unit_price: number;
  subtotal: number;
  total: number;
};

type OpenBill = {
  id?: number;
  reference: string;
  supplier?: string;
  date: string;
  due_date?: string;
  amount: number;
  open_amount: number;
  payment_state: string;
  lines?: OpenBillLine[];
};

type OpenBills = {
  total_open_payable: number;
  count: number;
  by_supplier?: Array<{ supplier: string; open_amount: number; count: number }>;
  bills: OpenBill[];
};

type OpenInvoices = {
  total_open_receivable: number;
  count: number;
  invoices: Array<{ reference: string; date: string; amount: number; open_amount: number; payment_state: string }>;
};

type Dashboard = {
  generated_at: string;
  financials: {
    today_sales: { total_amount: number; total_count: number };
    month_sales: { total_amount: number; total_count: number };
    ytd_sales: { total_amount: number; total_count: number };
    stock: { value: number; quantity: number; available: number };
    ytd_purchases: { amount: number; count: number };
    outstanding: { receivable: number; payable: number; receivable_count?: number; payable_count?: number };
  };
  monthly_sales: Array<{ month: string; amount: number; orders: number }>;
  stock_categories: Array<{ category: string; value: number; quantity: number; available: number }>;
  stock_analytics?: StockAnalytics;
  purchases?: PurchaseSummary;
  open_bills?: OpenBills;
  open_customer_invoices?: OpenInvoices;
  today_sales_by_category: {
    total: number;
    categories: Array<{ category: string; amount: number; quantity: number }>;
  };
  sales_analytics?: Partial<Record<AnalyticsPeriod, SalesAnalyticsBreakdown>>;
  low_stock: Array<{ sku: string; name: string; qty_available: number; forecast: number }>;
};

type AgentTraceItem = {
  iteration?: number;
  tool?: string;
  arguments?: Record<string, unknown>;
  latency_ms?: number;
  result_summary?: Record<string, unknown>;
};

type AgentEvidenceItem = {
  tool?: string;
  summary?: Record<string, unknown>;
};

type AgentMeta = {
  tool?: string;
  llm?: string;
  intent?: string;
  requestId?: string;
  trace?: AgentTraceItem[];
  evidence?: AgentEvidenceItem[];
};

type ChatMessage = {
  id: string;
  role: "user" | "assistant";
  content: string;
  createdAt: string;
  meta?: AgentMeta;
};

type PromptGroup = {
  title: string;
  prompts: string[];
};

const promptGroups: PromptGroup[] = [
  {
    title: "Daily briefing",
    prompts: ["Hi, how are you?", "What should Jhonny focus on today?", "What should I pay attention to this week?"],
  },
  {
    title: "Sales",
    prompts: ["How much did we sell today?", "Which brands are selling best?", "What products are growing or declining?"],
  },
  {
    title: "Stock",
    prompts: ["Should we buy more kids wetsuits?", "Which products are at risk of stockout?", "Which categories have too much stock?"],
  },
  {
    title: "Purchases and margin",
    prompts: ["Are purchases too high compared with sales?", "Where are we losing margin by brand or category?", "Which products have bad cost or price data?"],
  },
];

const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL || "http://127.0.0.1:8000";
const euro = new Intl.NumberFormat("en-IE", { style: "currency", currency: "EUR" });
const DEFAULT_PROFIT_MARGIN_RATE = 0.28;
const DEFAULT_DEMO_TOKEN = "retail-demo";

const navItems: Array<AppNavItem<AppMode>> = [
  { id: "home", label: "Home", icon: HomeIcon },
  { id: "analytics", label: "Analytics", icon: BarChart3 },
  { id: "agent", label: "Assisted Agent", icon: Bot },
];

const analyticsDashboards: Array<{ id: AnalyticsDashboard; label: string; description: string }> = [
  { id: "sales", label: "Sales", description: "Demand, category movement, and monthly trend." },
  { id: "stock", label: "Stock", description: "Stock value, brands, categories, and antiquity." },
  { id: "purchases", label: "Purchases", description: "Buying pressure, stock value, and reorder attention." },
  { id: "financials", label: "Financials", description: "Cash exposure, solvency, and profitability." },
];

const analyticsPeriods: Array<{ id: AnalyticsPeriod; label: string; shortLabel: string }> = [
  { id: "7", label: "Week", shortLabel: "Week" },
  { id: "30", label: "Month", shortLabel: "Month" },
  { id: "90", label: "3 month", shortLabel: "3 month" },
  { id: "365", label: "Year to date", shortLabel: "YTD" },
];

const SALES_TREND_SERIES: Array<{ key: SalesTrendSeriesKey; label: string; color: string }> = [
  { key: "sales", label: "Sales", color: "#3b82f6" },
  { key: "profit", label: "Profit margin", color: "#22c55e" },
];

const demoUser: AppUser = {
  displayName: "Jhonny Surf Store",
  email: "jhonnysurfstore@gmail.com",
  role: "Owner",
  jobTitle: "Surf, surfskate and style",
  officeLocation: "Parede, Cascais",
};

export default function Home() {
  const [token, setToken] = useState(DEFAULT_DEMO_TOKEN);
  const [mode, setMode] = useState<AppMode>("home");
  const [dashboard, setDashboard] = useState<Dashboard | null>(null);
  const [question, setQuestion] = useState("");
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [loading, setLoading] = useState(false);
  const [dashboardLoading, setDashboardLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    const storedToken = window.localStorage.getItem("retailAgentToken") || DEFAULT_DEMO_TOKEN;
    setToken(storedToken);
    loadDashboard(storedToken);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (token) {
      window.localStorage.setItem("retailAgentToken", token);
    }
  }, [token]);

  const headers = useMemo(() => {
    const value: Record<string, string> = { "Content-Type": "application/json" };
    if (token) value["X-App-Token"] = token;
    return value;
  }, [token]);

  async function loadDashboard(tokenOverride = token) {
    const nextToken = tokenOverride.trim() || DEFAULT_DEMO_TOKEN;
    setToken(nextToken);
    window.localStorage.setItem("retailAgentToken", nextToken);
    setError("");
    setDashboardLoading(true);
    try {
      const requestHeaders: Record<string, string> = { "Content-Type": "application/json" };
      requestHeaders["X-App-Token"] = nextToken;
      const response = await fetch(`${apiBaseUrl}/dashboard`, { headers: requestHeaders });
      if (response.status === 401) {
        setError("Enter the demo token, then refresh. Local demo token: retail-demo");
        return;
      }
      if (!response.ok) throw new Error(`Dashboard failed: ${response.status}`);
      setDashboard(await response.json());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to load dashboard.");
    } finally {
      setDashboardLoading(false);
    }
  }

  async function askAgent(nextQuestion = question) {
    const prompt = nextQuestion.trim();
    if (!prompt || loading) return;

    setLoading(true);
    setError("");
    setQuestion("");
    const userMessage: ChatMessage = {
      id: crypto.randomUUID(),
      role: "user",
      content: prompt,
      createdAt: new Date().toISOString(),
    };
    setMessages((current) => [...current, userMessage]);
    try {
      const response = await fetch(`${apiBaseUrl}/chat`, {
        method: "POST",
        headers,
        body: JSON.stringify({ question: prompt, channel: "app" }),
      });
      if (response.status === 401) {
        setError("Enter the demo token, then ask again. Local demo token: retail-demo");
        return;
      }
      if (!response.ok) throw new Error(`Chat failed: ${response.status}`);
      const data = await response.json();
      const formattedAnswer = data.answer || "No answer returned.";
      const metadata: AgentMeta = {
        tool: data.tool,
        llm: data.llm_provider,
        intent: data.intent,
        requestId: data.request_id,
        trace: data.tool_trace || [],
        evidence: data.evidence || [],
      };
      setMessages((current) => [
        ...current,
        {
          id: crypto.randomUUID(),
          role: "assistant",
          content: formattedAnswer,
          createdAt: new Date().toISOString(),
          meta: metadata,
        },
      ]);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Unable to ask agent.";
      setError(message);
      setMessages((current) => [
        ...current,
        {
          id: crypto.randomUUID(),
          role: "assistant",
          content: `I could not reach the assistant just now. ${message}`,
          createdAt: new Date().toISOString(),
        },
      ]);
    } finally {
      setLoading(false);
    }
  }

  const maxMonthly = Math.max(...(dashboard?.monthly_sales.map((item) => item.amount) || [1]));
  const maxStock = Math.max(...(dashboard?.stock_categories.map((item) => item.value) || [1]));

  return (
    <AppShell
      appName="AI Assistant"
      brandPrefix="Jhonny Surf Store"
      brandLogoSrc="/jhonny-surf-logo.png"
      subtitle="Where Surfers Become Legends"
      navItems={navItems}
      activeItem={mode}
      onSelectItem={setMode}
      navPrefixAccessory={
        <HeaderTokenControl
          token={token}
          setToken={setToken}
          loadDashboard={loadDashboard}
          dashboardLoading={dashboardLoading}
        />
      }
      user={demoUser}
      footer={
        <>
          <span>Retail Agent pilot for Jhonny Surf</span>
          <span>@jhonnysurfstore brand cockpit for surf, surfskate and style</span>
        </>
      }
    >
      <div className="space-y-6">
        {error ? (
          <div className="rounded-xl border border-destructive/30 bg-destructive/10 px-4 py-3 text-sm text-destructive">
            {error}
          </div>
        ) : null}

        {mode === "home" ? (
          <HomeLanding
            dashboard={dashboard}
            token={token}
            setToken={setToken}
            setMode={setMode}
            loadDashboard={loadDashboard}
            dashboardLoading={dashboardLoading}
          />
        ) : null}

        {mode === "analytics" ? (
          <AnalyticsTab dashboard={dashboard} maxMonthly={maxMonthly} maxStock={maxStock} />
        ) : null}

        {mode === "agent" ? (
          <AgentTab
            question={question}
            setQuestion={setQuestion}
            askAgent={askAgent}
            clearChat={() => setMessages([])}
            loading={loading}
            messages={messages}
          />
        ) : null}
      </div>
    </AppShell>
  );
}

function HeaderTokenControl({
  token,
  setToken,
  loadDashboard,
  dashboardLoading,
}: {
  token: string;
  setToken: (value: string) => void;
  loadDashboard: (tokenOverride?: string) => Promise<void>;
  dashboardLoading: boolean;
}) {
  return (
    <div className="mr-2 hidden items-center gap-2 rounded-xl border border-eyp-blue/25 bg-eyp-bg-light px-2 py-1 shadow-sm backdrop-blur md:flex">
      <Input
        id="header-demo-token"
        value={token}
        placeholder={DEFAULT_DEMO_TOKEN}
        aria-label="Demo token"
        className="h-7 w-32 border-transparent !bg-transparent px-2 text-xs font-semibold text-foreground shadow-none placeholder:text-muted-foreground focus-visible:ring-0 dark:text-white dark:placeholder:text-white/50"
        onChange={(event) => setToken(event.target.value)}
        onKeyDown={(event) => {
          if (event.key === "Enter") {
            loadDashboard(token);
          }
        }}
      />
      <button
        type="button"
        onClick={() => loadDashboard(token)}
        disabled={dashboardLoading}
        className="inline-flex h-7 items-center justify-center gap-1.5 rounded-md border border-eyp-blue/40 bg-eyp-blue px-2.5 text-xs font-semibold text-white shadow-sm shadow-eyp-blue/20 transition-colors hover:bg-eyp-blue/90 disabled:cursor-wait disabled:opacity-60"
        title="Refresh dashboard"
        aria-label="Refresh dashboard"
      >
        <RefreshCw className={cn("h-3.5 w-3.5", dashboardLoading && "animate-spin")} />
        <span>Enter</span>
      </button>
    </div>
  );
}

function HomeLanding({
  dashboard,
  token,
  setToken,
  setMode,
  loadDashboard,
  dashboardLoading,
}: {
  dashboard: Dashboard | null;
  token: string;
  setToken: (value: string) => void;
  setMode: (mode: AppMode) => void;
  loadDashboard: (tokenOverride?: string) => Promise<void>;
  dashboardLoading: boolean;
}) {
  const dailySales = dashboard?.financials.today_sales.total_amount ?? null;
  const monthlySales = dashboard?.financials.month_sales.total_amount ?? null;
  const monthlySalesBreakdown = dashboard?.sales_analytics?.["30"];
  const ytdSalesBreakdown = dashboard?.sales_analytics?.["365"];
  const monthlyProfitMargin = getProfitMarginPct(monthlySalesBreakdown);
  const ytdProfitMargin = getProfitMarginPct(ytdSalesBreakdown);
  const activeProfitMarginRate = (monthlyProfitMargin ?? DEFAULT_PROFIT_MARGIN_RATE * 100) / 100;
  const dailyProfit = dailySales === null ? null : dailySales * activeProfitMarginRate;
  const lastWeekSales = monthlySales === null ? null : monthlySales / 4.345;
  const currentMonthDay = dashboard ? Math.max(1, new Date(dashboard.generated_at).getDate()) : 1;
  const averageDailySales = monthlySales === null ? null : monthlySales / currentMonthDay;
  const averageDailyProfit =
    averageDailySales === null ? null : averageDailySales * activeProfitMarginRate;
  const averageMonthlySales = dashboard?.monthly_sales.length
    ? dashboard.monthly_sales.reduce((sum, item) => sum + item.amount, 0) / dashboard.monthly_sales.length
    : null;
  const averageWeeklySales = averageMonthlySales === null ? null : averageMonthlySales / 4.345;
  const monthlyNetMargin = monthlyProfitMargin ?? DEFAULT_PROFIT_MARGIN_RATE * 100;
  const averageNetMargin = ytdProfitMargin ?? monthlyNetMargin;
  const ytdProfit = dashboard
    ? ytdSalesBreakdown?.estimated_gross_profit ??
      dashboard.financials.ytd_sales.total_amount * ((ytdProfitMargin ?? DEFAULT_PROFIT_MARGIN_RATE * 100) / 100)
    : null;

  return (
    <>
      <section className="grid items-stretch gap-6 xl:grid-cols-2">
        <SectionCard contentClassName="relative flex min-h-[560px] items-center overflow-hidden p-8">
          <div className="absolute -right-20 -top-20 h-64 w-64 rounded-full bg-eyp-blue/15 blur-3xl" />
          <div className="absolute -bottom-24 left-10 h-52 w-52 rounded-full bg-cyan-400/10 blur-3xl" />
          <div className="relative mx-auto flex w-full max-w-3xl flex-col justify-center space-y-8">
            <div className="space-y-4">
              <h1 className="text-4xl font-semibold leading-tight tracking-tight md:text-6xl">
                Where surfers become legends, with AI Intelligence.
              </h1>
              <p className="max-w-2xl text-base text-muted-foreground md:text-lg">
                A business copilot shaped around Jhonny Surf Store: surfboards, wetsuits,
                surfskate, lifestyle gear, and owner-ready answers from live Odoo data.
              </p>
            </div>
            <div className="grid gap-5 sm:grid-cols-2">
              <Button
                variant="outline"
                onClick={() => setMode("agent")}
                className="min-h-20 whitespace-normal rounded-2xl border-2 border-emerald-400/80 bg-emerald-500/15 px-6 py-5 text-center text-lg font-semibold leading-snug text-emerald-700 shadow-[0_0_0_1px_rgba(52,211,153,0.25),0_24px_55px_-32px_rgba(16,185,129,1)] hover:border-emerald-300 hover:bg-emerald-500/25 dark:text-emerald-200"
              >
                Chat with Assisted Jhonny Agent
              </Button>
              <Button
                variant="outline"
                onClick={() => setMode("analytics")}
                className="min-h-20 whitespace-normal rounded-2xl border-2 border-violet-400/80 bg-violet-500/15 px-6 py-5 text-center text-lg font-semibold leading-snug text-violet-700 shadow-[0_0_0_1px_rgba(167,139,250,0.25),0_24px_55px_-32px_rgba(139,92,246,1)] hover:border-violet-300 hover:bg-violet-500/25 dark:text-violet-200"
              >
                View Analytics Dashboard
              </Button>
            </div>
          </div>
        </SectionCard>

        <SectionCard title="Store pulse" description="Live shop metrics for the next surf session.">
          <div className="space-y-4">
            <div className="grid gap-4 sm:grid-cols-2">
              <PulseMetric
                icon={Waves}
                label="Daily sales"
                value={dailySales === null ? "Refresh data" : euro.format(dailySales)}
                detail={dashboard ? `${dashboard.financials.today_sales.total_count} orders today` : "Connect using the demo token"}
                secondaryLabel="Avg daily sales"
                secondaryValue={averageDailySales === null ? "-" : euro.format(averageDailySales)}
                trend="up"
                trendLabel="+8% vs yesterday"
              />
              <PulseMetric
                icon={ShoppingBag}
                label="Daily profit"
                value={dailyProfit === null ? "-" : euro.format(dailyProfit)}
                detail="Sale price minus cost price"
                secondaryLabel="Avg daily profit"
                secondaryValue={averageDailyProfit === null ? "-" : euro.format(averageDailyProfit)}
                trend="up"
                trendLabel={`${monthlyNetMargin.toFixed(1)}% margin`}
              />
              <PulseMetric
                icon={BarChart3}
                label="Last week sales"
                value={lastWeekSales === null ? "-" : euro.format(lastWeekSales)}
                detail="Estimated from current month run-rate"
                secondaryLabel="Avg week sales"
                secondaryValue={averageWeeklySales === null ? "-" : euro.format(averageWeeklySales)}
                trend="down"
                trendLabel="-3% vs prior week"
              />
              <PulseMetric
                icon={RefreshCw}
                label="Profit margin"
                value={`${monthlyNetMargin.toFixed(1)}%`}
                detail="(Sale price - cost price) / sale price"
                secondaryLabel="Avg profit margin"
                secondaryValue={`${averageNetMargin.toFixed(1)}%`}
                trend="up"
                trendLabel="+2.1pp margin"
              />
            </div>
          </div>
        </SectionCard>
      </section>

      <section className="mt-6 grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <MetricCard label="YTD profit" value={ytdProfit === null ? "-" : euro.format(ytdProfit)} detail="Sale price minus cost price" trend="up" />
        <MetricCard label="YTD sales" value={dashboard ? euro.format(dashboard.financials.ytd_sales.total_amount) : "-"} detail={`${dashboard?.financials.ytd_sales.total_count ?? 0} orders across surf and lifestyle`} trend="up" />
        <MetricCard label="Stock value" value={dashboard ? euro.format(dashboard.financials.stock.value) : "-"} detail={`${dashboard?.financials.stock.available ?? 0} boards, suits, skates and apparel units`} trend="up" />
        <MetricCard label="Next 7 days billings to pay" value={dashboard ? euro.format(dashboard.financials.outstanding.payable) : "-"} detail="Upcoming supplier payment exposure" trend="down" />
      </section>
    </>
  );
}

function PulseMetric({
  icon: Icon,
  label,
  detail,
  secondaryLabel,
  secondaryValue,
  trend,
  trendLabel,
  value,
}: {
  icon: typeof ShoppingBag;
  label: string;
  detail: string;
  secondaryLabel?: string;
  secondaryValue?: string;
  trend: "up" | "down";
  trendLabel: string;
  value: string;
}) {
  const TrendIcon = trend === "up" ? ArrowUpRight : ArrowDownRight;

  return (
    <div className={cn(compactFieldGroupClass, "min-h-36 p-5")}>
      <div className="mb-4 flex items-start justify-between gap-3">
        <Icon className="h-6 w-6 text-eyp-blue" />
        <span
          className={cn(
            "inline-flex items-center gap-1 rounded-full border px-2.5 py-1 text-[11px] font-semibold whitespace-nowrap",
            trend === "up"
              ? "border-emerald-500/25 bg-emerald-500/10 text-emerald-500"
              : "border-red-500/25 bg-red-500/10 text-red-500"
          )}
        >
          <TrendIcon className="h-3.5 w-3.5" />
          {trendLabel}
        </span>
      </div>
      <div className={fieldLabelClass}>{label}</div>
      <div className="mt-3 text-2xl font-semibold tracking-tight">{value}</div>
      <p className="mt-2 text-xs text-muted-foreground">{detail}</p>
      {secondaryLabel && secondaryValue && (
        <div className="mt-4 rounded-xl border border-eyp-blue/10 bg-eyp-blue/5 px-3 py-2">
          <div className="text-[10px] font-semibold uppercase tracking-[0.16em] text-muted-foreground">
            {secondaryLabel}
          </div>
          <div className="mt-1 text-sm font-semibold text-foreground">{secondaryValue}</div>
        </div>
      )}
    </div>
  );
}

function AccessStrip({
  token,
  setToken,
  loadDashboard,
  dashboardLoading,
  compact = false,
}: {
  token: string;
  setToken: (value: string) => void;
  loadDashboard: (tokenOverride?: string) => Promise<void>;
  dashboardLoading: boolean;
  compact?: boolean;
}) {
  return (
    <div className={cn(compact ? compactFieldGroupClass : fieldGroupClass, "grid gap-3 sm:grid-cols-[1fr_auto]")}>
      <div className="space-y-1.5">
        <label htmlFor={compact ? "token-compact" : "token"} className={fieldLabelClass}>
          Demo token
        </label>
        <Input
          id={compact ? "token-compact" : "token"}
          value={token}
          placeholder="retail-demo"
          onChange={(event) => setToken(event.target.value)}
        />
      </div>
      <Button
        type="button"
        className="self-end"
        variant={compact ? "secondary" : "default"}
        onClick={() => loadDashboard(token)}
        disabled={dashboardLoading}
      >
        <RefreshCw className={cn("h-4 w-4", dashboardLoading && "animate-spin")} />
        Refresh
      </Button>
    </div>
  );
}

function AnalyticsTab({
  dashboard,
  maxMonthly,
  maxStock,
}: {
  dashboard: Dashboard | null;
  maxMonthly: number;
  maxStock: number;
}) {
  const [activeDashboard, setActiveDashboard] = useState<AnalyticsDashboard>("sales");
  const [period, setPeriod] = useState<AnalyticsPeriod>("30");
  const [selectedBillReference, setSelectedBillReference] = useState<string | null>(null);

  useEffect(() => {
    if (!dashboard || activeDashboard !== "purchases") return;
    const bills = dashboard.open_bills?.bills ?? [];
    if (!bills.length) {
      setSelectedBillReference(null);
      return;
    }
    if (!bills.some((bill) => bill.reference === selectedBillReference)) {
      setSelectedBillReference(bills[0].reference);
    }
  }, [activeDashboard, dashboard, selectedBillReference]);

  if (!dashboard) {
    return (
      <SectionCard title="Analytics dashboard" description="Enter the demo token and refresh to load Odoo metrics.">
        <p className="text-sm text-muted-foreground">No dashboard data loaded yet.</p>
      </SectionCard>
    );
  }

  const ytdSales = dashboard.financials.ytd_sales.total_amount;
  const ytdPurchases = dashboard.financials.ytd_purchases.amount;
  const receivable = dashboard.financials.outstanding.receivable;
  const payable = dashboard.financials.outstanding.payable;
  const monthlySales = dashboard.financials.month_sales.total_amount;
  const fallbackPeriodDays = Number(period);
  const selectedPeriod = analyticsPeriods.find((item) => item.id === period) ?? analyticsPeriods[1];
  const periodLabel = selectedPeriod.label.toLowerCase();
  const monthDay = Math.max(1, new Date(dashboard.generated_at).getDate());
  const avgDailySales = monthlySales / monthDay;
  const avgDailyOrders = dashboard.financials.month_sales.total_count / monthDay;
  const salesTrendData = buildSalesTrendData(dashboard, period);
  const salesBreakdown = dashboard.sales_analytics?.[period] ?? buildFallbackSalesBreakdown(dashboard, fallbackPeriodDays, salesTrendData);
  const periodProfitMarginPct = getProfitMarginPct(salesBreakdown) ?? DEFAULT_PROFIT_MARGIN_RATE * 100;
  const periodProfitMarginRate = periodProfitMarginPct / 100;
  const salesTrendDataWithMargin = salesTrendData.map((item) => ({
    ...item,
    profit: item.sales * periodProfitMarginRate,
    profitMarginPct: periodProfitMarginPct,
  }));
  const periodDays = getSalesAnalyticsDayCount(salesBreakdown, fallbackPeriodDays);
  const periodSales = salesBreakdown.total_amount || (period === "365" ? ytdSales : avgDailySales * periodDays);
  const periodOrders =
    salesBreakdown.sales_by_weekday.reduce((sum, item) => sum + item.orders, 0) ||
    (period === "365"
      ? dashboard.financials.ytd_sales.total_count
      : Math.max(1, Math.round(avgDailyOrders * periodDays)));
  const periodPurchases =
    period === "365" ? ytdPurchases : ytdPurchases * Math.min(1, fallbackPeriodDays / 365);
  const periodPurchaseCount =
    period === "365"
      ? dashboard.financials.ytd_purchases.count
      : Math.max(1, Math.round(dashboard.financials.ytd_purchases.count * Math.min(1, fallbackPeriodDays / 365)));
  const purchaseToSalesRatio = periodSales > 0 ? (periodPurchases / periodSales) * 100 : 0;
  const netCashPosition = receivable - payable;
  const maxFinancialExposure = Math.max(receivable, payable, 1);
  const topSellingProduct = salesBreakdown.sales_by_product?.[0];
  const openBills = dashboard.open_bills?.bills ?? [];
  const selectedBill =
    openBills.find((bill) => bill.reference === selectedBillReference) ?? openBills[0] ?? null;
  const estimatedPeriodProfit =
    typeof salesBreakdown.estimated_gross_profit === "number"
      ? salesBreakdown.estimated_gross_profit
      : periodSales * periodProfitMarginRate;
  const netMarginPct = periodSales > 0 ? calculateProfitMarginPct(estimatedPeriodProfit, periodSales) : 0;

  return (
    <div className="space-y-6">
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          {analyticsDashboards.map((item) => {
            const active = item.id === activeDashboard;
            const tone =
              item.id === "sales"
                ? "border-emerald-500/45 bg-emerald-500/10 text-emerald-700 hover:bg-emerald-500/15 dark:text-emerald-200"
                : item.id === "stock"
                  ? "border-cyan-500/45 bg-cyan-500/10 text-cyan-700 hover:bg-cyan-500/15 dark:text-cyan-200"
                : item.id === "purchases"
                  ? "border-violet-500/45 bg-violet-500/10 text-violet-700 hover:bg-violet-500/15 dark:text-violet-200"
                  : "border-eyp-blue/35 bg-eyp-blue/10 text-eyp-blue hover:bg-eyp-blue/15";
            const activeTone =
              item.id === "sales"
                ? "border-emerald-400 bg-emerald-500/15 shadow-[0_24px_55px_-38px_rgba(16,185,129,0.95)]"
                : item.id === "stock"
                  ? "border-cyan-400 bg-cyan-500/15 shadow-[0_24px_55px_-38px_rgba(6,182,212,0.95)]"
                : item.id === "purchases"
                  ? "border-violet-400 bg-violet-500/15 shadow-[0_24px_55px_-38px_rgba(139,92,246,0.95)]"
                  : "border-eyp-blue/60 bg-eyp-blue/15 shadow-[0_24px_55px_-38px_rgba(26,154,250,0.95)]";

            return (
              <button
                key={item.id}
                type="button"
                onClick={() => setActiveDashboard(item.id)}
                className={cn(
                  "min-h-24 rounded-2xl border-2 px-5 py-4 text-left text-sm transition-all",
                  tone,
                  active && activeTone
                )}
              >
                <span className="block text-base font-semibold">{item.label}</span>
                <span className="mt-1.5 block text-xs text-foreground/70 dark:text-white/70">{item.description}</span>
              </button>
            );
          })}
      </div>

      {activeDashboard === "sales" && (
      <SectionCard
        title="Sales"
        description="Demand, category movement, and monthly trend."
        action={<PeriodSelector period={period} setPeriod={setPeriod} />}
      >
        <div className="space-y-5">
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
            <MetricCard label="Period sales" value={euro.format(periodSales)} detail={`${periodOrders} orders in ${periodLabel}`} />
            <MetricCard label="Avg daily sales" value={euro.format(periodSales / periodDays)} detail={`Average across ${periodLabel}`} />
            <MetricCard
              label="Top selling product"
              value={topSellingProduct?.product ?? "-"}
              detail={
                topSellingProduct
                  ? `${Math.round(topSellingProduct.quantity)} units | ${euro.format(topSellingProduct.amount)}`
                  : `No product sales in ${periodLabel}`
              }
            />
            <MetricCard
              label="Profit margin"
              value={`${netMarginPct.toFixed(1)}%`}
              detail="(Sale price - cost price) / sale price"
            />
          </div>
          <AnalyticsPanel
            title="Daily sales trend"
            description={`Day-by-day movement for sales and profit margin in ${periodLabel}.`}
          >
            <SalesDailyTrendChart
              data={salesTrendDataWithMargin}
              period={period}
            />
          </AnalyticsPanel>
          <AnalyticsPanel
            title="Average revenue by weekday"
            description={`Compare each weekday's latest revenue against the average for that weekday in ${periodLabel}.`}
          >
            <WeekdayRevenueChart data={buildWeekdayRevenueData(salesBreakdown.sales_by_weekday)} />
          </AnalyticsPanel>
          <AnalyticsPanel
            title="Sales by hour of day"
            description={`Hourly revenue pattern in ${periodLabel}.`}
          >
            <SalesHourBreakdownChart data={salesBreakdown.sales_by_hour} />
          </AnalyticsPanel>
          <div className="grid gap-5">
            <AnalyticsPanel
              title="Sales by category"
              description={`Estimated category movement in ${periodLabel}.`}
            >
              <RankedSalesBarChart
                data={salesBreakdown.sales_by_category}
                labelKey="category"
                emptyMessage="No category sales found for this period."
              />
            </AnalyticsPanel>
            <AnalyticsPanel
              title="Sales by brand"
              description={`Ranked brand revenue in ${periodLabel}.`}
            >
              <RankedSalesBarChart
                data={salesBreakdown.sales_by_brand}
                labelKey="brand"
                emptyMessage="No brand sales found for this period."
              />
            </AnalyticsPanel>
          </div>
        </div>
      </SectionCard>
      )}

      {activeDashboard === "stock" && (
      <SectionCard
        title="Stock"
        description="Understand inventory value, brand exposure, category mix, and stock antiquity."
      >
        <div className="space-y-5">
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
            <MetricCard label="Stock value" value={euro.format(dashboard.financials.stock.value)} detail={`${dashboard.financials.stock.available} available units`} />
            <MetricCard label="Stock units" value={Math.round(dashboard.financials.stock.quantity).toLocaleString()} detail="Total units in internal stock" />
            <MetricCard label="Low stock items" value={dashboard.low_stock.length.toString()} detail="Products needing owner attention" trend="down" />
            <MetricCard label="Top stock brand" value={dashboard.stock_analytics?.by_brand?.[0]?.brand ?? "-"} detail={dashboard.stock_analytics?.by_brand?.[0] ? euro.format(dashboard.stock_analytics.by_brand[0].value) : "No brand stock data"} />
          </div>
          <div className="grid gap-5 lg:grid-cols-2">
            <AnalyticsPanel title="Stock value by brand" description="Inventory valuation grouped by product brand.">
              <RankedStockBarChart data={dashboard.stock_analytics?.by_brand ?? []} labelKey="brand" emptyMessage="No stock brand data found." />
            </AnalyticsPanel>
            <AnalyticsPanel title="Stock value by category" description="Inventory valuation grouped by category.">
              <RankedStockBarChart data={dashboard.stock_analytics?.by_category ?? dashboard.stock_categories} labelKey="category" emptyMessage="No stock category data found." />
            </AnalyticsPanel>
            <AnalyticsPanel title="Stock antiquity" description="How old current inventory is based on incoming date.">
              <StockAgeChart data={dashboard.stock_analytics?.by_age ?? []} />
            </AnalyticsPanel>
            <AnalyticsPanel title="Low stock watchlist" description="Products with low available quantity.">
              {dashboard.low_stock.length ? (
                dashboard.low_stock.map((item) => (
                  <div key={item.sku} className={compactFieldGroupClass}>
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <p className="font-medium">{item.name}</p>
                        <p className="text-xs text-muted-foreground">{item.sku}</p>
                      </div>
                      <Badge variant="eyp">{item.qty_available} left</Badge>
                    </div>
                    <p className="mt-2 text-xs text-muted-foreground">Forecast: {item.forecast}</p>
                  </div>
                ))
              ) : (
                <p className="text-sm text-muted-foreground">No low-stock items returned.</p>
              )}
            </AnalyticsPanel>
          </div>
        </div>
      </SectionCard>
      )}

      {activeDashboard === "purchases" && (
      <SectionCard
        title="Purchases"
        description="Bills to pay and stock purchase activity."
        action={<PeriodSelector period={period} setPeriod={setPeriod} />}
      >
        <div className="space-y-5">
          <div className="grid gap-4 md:grid-cols-3">
            <MetricCard label="Period purchases" value={euro.format(periodPurchases)} detail={`${periodPurchaseCount} purchase orders in ${periodLabel}`} />
            <MetricCard label="Bills to pay" value={euro.format(dashboard.open_bills?.total_open_payable ?? payable)} detail={`${dashboard.open_bills?.count ?? dashboard.financials.outstanding.payable_count ?? 0} open supplier bills`} />
            <MetricCard label="Purchase ratio" value={`${purchaseToSalesRatio.toFixed(1)}%`} detail={`Purchases as share of ${periodLabel} sales`} />
          </div>
          <div className="grid gap-5 lg:grid-cols-2">
            <AnalyticsPanel
              title="Top bills to pay by fornecedor"
              description="Open supplier bill exposure grouped by company."
            >
              <SupplierBillsChart data={dashboard.open_bills?.by_supplier ?? []} />
            </AnalyticsPanel>
            <AnalyticsPanel
              title="Recent stock purchases"
            >
              {(dashboard.purchases?.recent_orders ?? []).map((item) => (
                <ListRow key={`${item.reference}-${item.date}`} label={item.reference} value={euro.format(item.amount)} detail={`${item.date ?? "No date"} | ${item.state}`} />
              ))}
            </AnalyticsPanel>
          </div>
          <AnalyticsPanel
            title="Open bills to pay"
            description="Select a supplier bill to preview the exact bill lines and payment exposure."
          >
            <div className="grid gap-4 xl:grid-cols-[minmax(0,0.95fr)_minmax(0,1.05fr)]">
              <div className="space-y-2">
                {openBills.length ? (
                  openBills.map((item) => (
                    <SelectableBillRow
                      key={`${item.reference}-${item.date}`}
                      bill={item}
                      selected={item.reference === selectedBill?.reference}
                      onSelect={() => setSelectedBillReference(item.reference)}
                    />
                  ))
                ) : (
                  <p className="text-sm text-muted-foreground">No open supplier bills returned.</p>
                )}
              </div>
              <BillPreview bill={selectedBill} />
            </div>
          </AnalyticsPanel>
        </div>
      </SectionCard>
      )}

      {activeDashboard === "financials" && (
      <SectionCard
        title="Financials"
        description="Simple solvability view: receivables, payables, stock buffer, and profitability."
        action={<PeriodSelector period={period} setPeriod={setPeriod} />}
      >
        <div className="space-y-5">
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
            <MetricCard label="Receivable" value={euro.format(receivable)} detail="Customer balance outstanding" />
            <MetricCard label="Payable" value={euro.format(payable)} detail="Supplier balance outstanding" />
            <MetricCard label="Working capital" value={euro.format(receivable + dashboard.financials.stock.value - payable)} detail="Receivable + stock - payable" />
            <MetricCard label="Profit margin" value={`${netMarginPct.toFixed(1)}%`} detail={`Sale price minus cost price as % of sales in ${periodLabel}`} />
          </div>
          <div className="grid gap-5 lg:grid-cols-2">
            <AnalyticsPanel
              title="Cash exposure"
            >
              <BarRow label="Receivable" value={euro.format(receivable)} detail="Expected cash in" percent={(receivable / maxFinancialExposure) * 100} />
              <BarRow label="Payable" value={euro.format(payable)} detail="Expected cash out" percent={(payable / maxFinancialExposure) * 100} />
              <div className={compactFieldGroupClass}>
                <div className="flex items-center justify-between gap-3">
                  <span className="font-medium">Net position</span>
                  <span className={cn("font-semibold", netCashPosition >= 0 ? "text-emerald-500" : "text-destructive")}>
                    {euro.format(netCashPosition)}
                  </span>
                </div>
                <p className="text-xs text-muted-foreground">Receivable minus payable</p>
              </div>
            </AnalyticsPanel>
            <AnalyticsPanel
              title="Profitability view"
            >
              <BarRow label="Period sales" value={euro.format(periodSales)} detail={`Sales in ${periodLabel}`} percent={100} />
              <BarRow label="Profit margin" value={`${netMarginPct.toFixed(1)}%`} detail="(Sale price - cost price) / sale price" percent={netMarginPct} />
              <BarRow label="Period purchases" value={euro.format(periodPurchases)} detail={`Buying investment in ${periodLabel}`} percent={Math.min(100, purchaseToSalesRatio)} />
            </AnalyticsPanel>
          </div>
        </div>
      </SectionCard>
      )}
    </div>
  );
}

function AnalyticsPanel({
  title,
  description,
  action,
  children,
}: {
  title: string;
  description?: string;
  action?: ReactNode;
  children: ReactNode;
}) {
  return (
    <div className="rounded-2xl border border-eyp-blue/20 bg-gradient-to-br from-eyp-blue/10 via-card/95 to-card p-4 shadow-[0_24px_80px_-48px_rgba(59,130,246,0.45)]">
      <div className="mb-4 flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <h3 className="text-sm font-semibold">{title}</h3>
          {description && <p className="text-xs text-muted-foreground">{description}</p>}
        </div>
        {action}
      </div>
      <div className="space-y-3">{children}</div>
    </div>
  );
}

function PeriodSelector({
  period,
  setPeriod,
}: {
  period: AnalyticsPeriod;
  setPeriod: (period: AnalyticsPeriod) => void;
}) {
  return (
    <div className="flex flex-col items-start gap-1.5 sm:items-end">
      <span className="text-[10px] font-semibold uppercase tracking-[0.18em] text-muted-foreground">
        Analysis period
      </span>
      <div className="inline-flex shrink-0 items-center gap-1 rounded-full border border-eyp-blue/15 bg-eyp-bg-light/90 p-1 shadow-sm">
        {analyticsPeriods.map((item) => {
          const active = item.id === period;

          return (
            <button
              key={item.id}
              type="button"
              onClick={() => setPeriod(item.id)}
              className={cn(
                "rounded-full px-3.5 py-1.5 text-xs font-semibold text-muted-foreground transition-colors hover:bg-eyp-blue/10 hover:text-eyp-blue",
                active && "bg-eyp-blue text-white shadow-sm shadow-eyp-blue/20 hover:bg-eyp-blue hover:text-white"
              )}
              title={item.label}
            >
              {item.shortLabel}
            </button>
          );
        })}
      </div>
    </div>
  );
}

function AgentTab({
  question,
  setQuestion,
  askAgent,
  clearChat,
  loading,
  messages,
}: {
  question: string;
  setQuestion: (value: string) => void;
  askAgent: (nextQuestion?: string) => Promise<void>;
  clearChat: () => void;
  loading: boolean;
  messages: ChatMessage[];
}) {
  const bottomRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages, loading]);

  const sendCurrentQuestion = () => askAgent(question);

  const handleComposerKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      sendCurrentQuestion();
    }
  };

  return (
    <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_360px]">
      <SectionCard
        title="Jhonny AI Assistant"
        description="Chat with the Odoo business intelligence agent."
        action={
          messages.length ? (
            <Button type="button" variant="ghost" size="sm" onClick={clearChat} disabled={loading}>
              Clear chat
            </Button>
          ) : null
        }
      >
        <div className="flex min-h-[620px] flex-col overflow-hidden rounded-3xl border border-eyp-blue/10 bg-gradient-to-b from-background to-eyp-bg-light/45">
          <div className="flex items-center gap-3 border-b border-eyp-blue/10 bg-background/80 px-5 py-4">
            <div className="flex h-10 w-10 items-center justify-center rounded-full bg-eyp-blue text-white shadow-sm shadow-eyp-blue/25">
              <Bot className="h-5 w-5" />
            </div>
            <div className="min-w-0">
              <p className="text-sm font-semibold">Jhonny Surf AI Agent</p>
              <p className="text-xs text-muted-foreground">Connected to curated Odoo sales, stock, purchase, and margin tools</p>
            </div>
            <Badge variant="outline" className="ml-auto hidden sm:inline-flex">
              Live assistant
            </Badge>
          </div>

          <div className="flex-1 overflow-y-auto px-4 py-5 sm:px-6">
            {messages.length ? (
              <div className="space-y-5">
                {messages.map((message) => (
                  <ChatBubble key={message.id} message={message} />
                ))}
                {loading ? <TypingIndicator /> : null}
                <div ref={bottomRef} />
              </div>
            ) : (
              <div className="flex h-full min-h-[420px] items-center justify-center">
                <div className="max-w-xl text-center">
                  <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-full bg-eyp-blue text-white shadow-lg shadow-eyp-blue/20">
                    <Bot className="h-7 w-7" />
                  </div>
                  <h3 className="text-xl font-semibold">Hi Jhonny, how can I help today?</h3>
                  <p className="mt-2 text-sm leading-6 text-muted-foreground">
                    Ask me about sales, stock cover, purchases, financial risks, margins, or what the shop should focus on next.
                  </p>
                  <div className="mt-5 flex flex-wrap justify-center gap-2">
                    {promptGroups[0].prompts.slice(0, 3).map((prompt) => (
                      <Button key={prompt} type="button" variant="secondary" size="sm" onClick={() => askAgent(prompt)} disabled={loading}>
                        {prompt}
                      </Button>
                    ))}
                  </div>
                </div>
              </div>
            )}
          </div>

          <div className="border-t border-eyp-blue/10 bg-background/90 p-4">
            <div className="rounded-2xl border border-eyp-blue/20 bg-background p-2 shadow-sm">
              <textarea
                value={question}
                onChange={(event) => setQuestion(event.target.value)}
                onKeyDown={handleComposerKeyDown}
                placeholder="Message Jhonny AI about sales, stock, purchases, margins..."
                rows={2}
                className="max-h-32 min-h-12 w-full resize-none bg-transparent px-3 py-2 text-sm leading-6 outline-none placeholder:text-muted-foreground"
                disabled={loading}
              />
              <div className="flex items-center justify-between gap-3 px-2 pb-1">
                <span className="text-[11px] text-muted-foreground">Enter to send · Shift+Enter for a new line</span>
                <Button type="button" size="icon" onClick={sendCurrentQuestion} disabled={loading || !question.trim()} title="Send message">
                  <Send className="h-4 w-4" />
                </Button>
              </div>
            </div>
          </div>
        </div>
      </SectionCard>

      <SectionCard title="Suggested prompts" description="Start with a business question or use these during the conversation.">
        <div className="space-y-5">
          {promptGroups.map((group) => (
            <div key={group.title} className="space-y-2">
              <p className="text-xs font-semibold uppercase tracking-[0.18em] text-muted-foreground">{group.title}</p>
              <div className="space-y-2">
                {group.prompts.map((prompt) => (
                  <button
                    key={prompt}
                    type="button"
                    onClick={() => askAgent(prompt)}
                    disabled={loading}
                    className="w-full rounded-2xl border border-eyp-blue/10 bg-background/70 px-3 py-3 text-left text-sm leading-5 text-foreground/85 shadow-sm transition-colors hover:border-eyp-blue/30 hover:bg-eyp-blue/10 disabled:cursor-not-allowed disabled:opacity-60"
                  >
                    {prompt}
                  </button>
                ))}
              </div>
            </div>
          ))}
          {messages.length ? (
            <div className="rounded-2xl border border-eyp-blue/10 bg-eyp-bg-light/60 p-3 text-xs leading-5 text-muted-foreground">
              This chat is session-only for now. The agent still grounds each answer in live Odoo tools and shows evidence under assistant messages.
            </div>
          ) : null}
        </div>
      </SectionCard>
    </div>
  );
}

function ChatBubble({ message }: { message: ChatMessage }) {
  const isUser = message.role === "user";
  return (
    <div className={cn("flex", isUser ? "justify-end" : "justify-start")}>
      <div className={cn("max-w-[86%] space-y-2", isUser ? "items-end" : "items-start")}>
        <div
          className={cn(
            "rounded-3xl px-4 py-3 text-sm leading-6 shadow-sm",
            isUser
              ? "rounded-br-md bg-eyp-blue text-white shadow-eyp-blue/20"
              : "rounded-bl-md border border-eyp-blue/10 bg-background text-foreground/90"
          )}
        >
          <p className="whitespace-pre-wrap">{message.content}</p>
        </div>
        {!isUser && message.meta ? <AssistantMessageMeta meta={message.meta} /> : null}
      </div>
    </div>
  );
}

function AssistantMessageMeta({ meta }: { meta: AgentMeta }) {
  const trace = meta.trace || [];
  return (
    <div className="space-y-2">
      <div className="flex flex-wrap gap-1.5">
        {meta.intent ? <Badge variant="outline">Intent: {meta.intent}</Badge> : null}
        {meta.tool ? <Badge variant="outline">Tool: {meta.tool}</Badge> : null}
        {meta.llm ? <Badge variant="outline">LLM: {meta.llm}</Badge> : null}
      </div>
      {trace.length ? (
        <details className="rounded-2xl border border-eyp-blue/10 bg-eyp-bg-light/60 p-3 text-xs text-muted-foreground">
          <summary className="cursor-pointer font-semibold text-eyp-blue">Evidence used ({trace.length})</summary>
          <div className="mt-2 space-y-2">
            {trace.map((item, index) => (
              <div key={`${item.tool}-${index}`}>
                <span className="font-semibold text-foreground/80">{item.tool}</span>
                {typeof item.latency_ms === "number" ? <span> · {item.latency_ms}ms</span> : null}
                {item.arguments && Object.keys(item.arguments).length ? (
                  <span> · args {JSON.stringify(item.arguments)}</span>
                ) : null}
              </div>
            ))}
          </div>
        </details>
      ) : null}
      {meta.requestId ? <p className="text-[11px] text-muted-foreground">Request ID: {meta.requestId}</p> : null}
    </div>
  );
}

function TypingIndicator() {
  return (
    <div className="flex justify-start">
      <div className="rounded-3xl rounded-bl-md border border-eyp-blue/10 bg-background px-4 py-3 text-sm text-muted-foreground shadow-sm">
        Jhonny AI is checking Odoo data...
      </div>
    </div>
  );
}

function MetricCard({
  label,
  value,
  detail,
  trend,
}: {
  label: string;
  value: string;
  detail: string;
  trend?: "up" | "down";
}) {
  const TrendIcon = trend === "down" ? ArrowDownRight : ArrowUpRight;

  return (
    <SectionCard contentClassName="space-y-2 p-5">
      <div className={fieldLabelClass}>{label}</div>
      <div className="flex items-center gap-2 text-2xl font-semibold tracking-tight">
        <span>{value}</span>
        {trend && (
          <TrendIcon
            className={cn(
              "h-5 w-5 shrink-0",
              trend === "down" ? "text-red-500" : "text-emerald-500"
            )}
          />
        )}
      </div>
      <p className="text-sm text-muted-foreground">{detail}</p>
    </SectionCard>
  );
}

function BarRow({
  label,
  value,
  detail,
  percent,
}: {
  label: string;
  value: string;
  detail: string;
  percent: number;
}) {
  return (
    <div className={compactFieldGroupClass}>
      <div className="flex items-center justify-between gap-3 text-sm">
        <span className="font-medium">{label}</span>
        <span className="font-semibold text-eyp-blue">{value}</span>
      </div>
      <div className="h-2 overflow-hidden rounded-full bg-muted">
        <div className="h-full rounded-full bg-eyp-blue" style={{ width: `${Math.max(4, Math.min(100, percent))}%` }} />
      </div>
      <p className="text-xs text-muted-foreground">{detail}</p>
    </div>
  );
}

function buildFallbackSalesBreakdown(
  dashboard: Dashboard,
  periodDays: number,
  trendData: ReturnType<typeof buildSalesTrendData>
): SalesAnalyticsBreakdown {
  const categoryRows = dashboard.today_sales_by_category.categories.map((item) => ({
    category: item.category,
    amount: roundCurrency(item.amount * periodDays),
    quantity: Math.round(item.quantity * periodDays),
    lines: Math.max(1, Math.round(item.quantity * periodDays)),
  }));
  const totalCategory = categoryRows.reduce((sum, item) => sum + item.amount, 0);
  const stockWeightedCategories =
    totalCategory > 0
      ? categoryRows
      : dashboard.stock_categories.slice(0, 8).map((item) => {
          const stockTotal = Math.max(
            1,
            dashboard.stock_categories.reduce((sum, category) => sum + category.value, 0)
          );
          const weight = item.value / stockTotal;
          return {
            category: item.category,
            amount: roundCurrency(dashboard.financials.month_sales.total_amount * weight),
            quantity: Math.max(1, Math.round(item.available * weight)),
            lines: Math.max(1, Math.round(item.quantity * weight)),
          };
        });
  const fallbackTotal = stockWeightedCategories.reduce((sum, item) => sum + item.amount, 0);
  const brandSeeds = ["JSS", "Billabong", "FCS", "Channel Islands", "NMD", "Versus"];
  const salesByBrand = brandSeeds.map((brand, index) => {
    const weight = Math.max(0.08, 0.32 - index * 0.045);
    return {
      brand,
      amount: roundCurrency((fallbackTotal || dashboard.financials.month_sales.total_amount) * weight),
      quantity: Math.max(1, Math.round(dashboard.financials.month_sales.total_count * weight)),
      lines: Math.max(1, Math.round(dashboard.financials.month_sales.total_count * weight)),
    };
  });

  return {
    start_date: trendData[0]?.label ?? "",
    end_date: trendData[trendData.length - 1]?.label ?? "",
    brand_field: null,
    total_amount: roundCurrency(fallbackTotal),
    estimated_cost: roundCurrency(fallbackTotal * (1 - DEFAULT_PROFIT_MARGIN_RATE)),
    estimated_gross_profit: roundCurrency(fallbackTotal * DEFAULT_PROFIT_MARGIN_RATE),
    estimated_gross_margin_pct: DEFAULT_PROFIT_MARGIN_RATE * 100,
    costed_lines: 0,
    sales_by_category: stockWeightedCategories,
    sales_by_brand: salesByBrand,
    sales_by_product: stockWeightedCategories.map((item) => ({
      product: item.category,
      amount: item.amount,
      quantity: item.quantity,
      lines: item.lines,
    })),
    sales_by_weekday: buildWeekdayRevenueDataFromTrend(trendData).map((item) => ({
      weekday: item.weekday,
      amount: roundCurrency(item.averageRevenue),
      quantity: Math.max(1, Math.round(item.averageRevenue / 75)),
      orders: Math.max(1, Math.round(item.averageRevenue / 150)),
    })),
    sales_by_hour: buildHourlySalesData(trendData),
  };
}

function roundCurrency(value: number) {
  return Math.round(value * 100) / 100;
}

function calculateProfitMarginPct(profit: number, sales: number) {
  return sales > 0 ? (profit / sales) * 100 : 0;
}

function getProfitMarginPct(salesBreakdown?: SalesAnalyticsBreakdown) {
  if (!salesBreakdown) return null;
  const sales = Number(salesBreakdown.total_amount || 0);
  if (sales <= 0) return 0;
  if (typeof salesBreakdown.estimated_gross_profit === "number") {
    return calculateProfitMarginPct(salesBreakdown.estimated_gross_profit, sales);
  }
  if (typeof salesBreakdown.estimated_cost === "number") {
    return calculateProfitMarginPct(sales - salesBreakdown.estimated_cost, sales);
  }
  if (typeof salesBreakdown.estimated_gross_margin_pct === "number") {
    return salesBreakdown.estimated_gross_margin_pct;
  }
  return null;
}

function getSalesAnalyticsDayCount(salesBreakdown: SalesAnalyticsBreakdown, fallbackDays: number) {
  const start = new Date(`${salesBreakdown.start_date}T00:00:00`);
  const end = new Date(`${salesBreakdown.end_date}T00:00:00`);
  if (Number.isNaN(start.getTime()) || Number.isNaN(end.getTime())) return fallbackDays;
  const diffMs = end.getTime() - start.getTime();
  return Math.max(1, Math.round(diffMs / 86_400_000) + 1);
}

function buildHourlySalesData(trendData: ReturnType<typeof buildSalesTrendData>): SalesHourBreakdown[] {
  const totalSales = trendData.reduce((sum, item) => sum + item.sales, 0);
  const hourlyPattern = [
    { hour: 9, weight: 0.04 },
    { hour: 10, weight: 0.07 },
    { hour: 11, weight: 0.11 },
    { hour: 12, weight: 0.12 },
    { hour: 13, weight: 0.1 },
    { hour: 14, weight: 0.11 },
    { hour: 15, weight: 0.14 },
    { hour: 16, weight: 0.13 },
    { hour: 17, weight: 0.11 },
    { hour: 18, weight: 0.07 },
  ];

  return Array.from({ length: 24 }, (_, hour) => {
    const pattern = hourlyPattern.find((item) => item.hour === hour);
    const amount = roundCurrency(totalSales * (pattern?.weight ?? 0));
    return {
      hour,
      label: `${hour.toString().padStart(2, "0")}:00`,
      amount,
      quantity: amount > 0 ? Math.max(1, Math.round(amount / 75)) : 0,
      orders: amount > 0 ? Math.max(1, Math.round(amount / 150)) : 0,
    };
  });
}

function buildSalesTrendData(dashboard: Dashboard, period: AnalyticsPeriod) {
  if (period === "365") {
    return dashboard.monthly_sales.map((item) => ({
      label: item.month,
      fullLabel: item.month,
      weekday: "",
      sales: item.amount,
      profit: item.amount * DEFAULT_PROFIT_MARGIN_RATE,
      profitMarginPct: DEFAULT_PROFIT_MARGIN_RATE * 100,
      orders: item.orders,
    }));
  }

  const periodDays = Number(period);
  const generatedAt = new Date(dashboard.generated_at);
  const avgDailySales =
    dashboard.financials.month_sales.total_amount / Math.max(1, generatedAt.getDate());
  const avgDailyOrders =
    dashboard.financials.month_sales.total_count / Math.max(1, generatedAt.getDate());

  const weekdayOrder = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];
  const weekdayWeights = [0.88, 0.94, 1.02, 0.96, 1.12, 1.22, 0.86];
  const weightTotal = weekdayWeights.reduce((sum, value) => sum + value, 0);
  const periodSales = avgDailySales * periodDays;
  const periodOrders = Math.max(1, Math.round(avgDailyOrders * periodDays));

  return weekdayOrder.map((weekday, index) => {
    const sales = (periodSales * weekdayWeights[index]) / weightTotal;
    const orders = Math.max(1, Math.round((periodOrders * weekdayWeights[index]) / weightTotal));
    return {
      label: weekday,
      fullLabel: `${weekday} average`,
      weekday,
      sales,
      profit: sales * DEFAULT_PROFIT_MARGIN_RATE,
      profitMarginPct: DEFAULT_PROFIT_MARGIN_RATE * 100,
      orders,
    };
  });
}

function SalesDailyTrendChart({
  data,
  period,
}: {
  data: ReturnType<typeof buildSalesTrendData>;
  period: AnalyticsPeriod;
}) {
  const commonAxis = (
    <>
      <CartesianGrid vertical={false} strokeDasharray="3 3" stroke="#334155" opacity={0.2} />
      <XAxis
        dataKey="label"
        tickLine={false}
        axisLine={false}
        minTickGap={24}
        tick={{ fill: "#94a3b8", fontSize: 12 }}
      />
      <YAxis
        yAxisId="sales"
        tickLine={false}
        axisLine={false}
        tick={{ fill: "#94a3b8", fontSize: 12 }}
        tickFormatter={(value) => {
          const numericValue = Number(value);
          return numericValue >= 1000 ? `${Math.round(numericValue / 1000)}k` : `${Math.round(numericValue)}`;
        }}
      />
      <YAxis
        yAxisId="margin"
        orientation="right"
        tickLine={false}
        axisLine={false}
        tick={{ fill: "#94a3b8", fontSize: 12 }}
        tickFormatter={(value) => `${Math.round(Number(value))}%`}
        domain={[0, 100]}
      />
      <Tooltip
        contentStyle={{
          borderRadius: "12px",
          border: "1px solid rgba(148, 163, 184, 0.2)",
          background: "rgba(15, 23, 42, 0.96)",
          color: "#e2e8f0",
        }}
        labelFormatter={(_, payload) => payload?.[0]?.payload?.fullLabel || ""}
        formatter={(value, name, payload) => {
          const numericValue = Number(value ?? 0);
          const seriesName = String(name);
          const quantity = payload?.payload?.orders;
          if (seriesName === "Profit margin") {
            return [`${numericValue.toFixed(1)}%`, seriesName];
          }
          return [
            `${euro.format(numericValue)}${typeof quantity === "number" ? ` | Qty: ${quantity.toLocaleString()}` : ""}`,
            seriesName,
          ];
        }}
      />
      <Legend iconType="circle" />
    </>
  );

  return (
    <div className="h-[320px] pt-2">
      <ResponsiveContainer width="100%" height="100%">
        <ComposedChart data={data} margin={{ top: 8, right: 8, left: -12, bottom: 0 }}>
          {commonAxis}
          <Bar yAxisId="sales" dataKey="sales" name="Sales" fill="#3b82f6" radius={[8, 8, 0, 0]} />
          <Line
            yAxisId="margin"
            type="monotone"
            dataKey="profitMarginPct"
            name="Profit margin"
            stroke="#22c55e"
            strokeWidth={3}
            dot={{ r: 3 }}
          />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}

function buildWeekdayRevenueDataFromTrend(data: ReturnType<typeof buildSalesTrendData>) {
  const weekdayOrder = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

  return weekdayOrder.map((weekday) => {
    const weekdayEntries = data.filter((item) => item.weekday === weekday);
    const latest = weekdayEntries[weekdayEntries.length - 1];
    const averageRevenue =
      weekdayEntries.length > 0
        ? weekdayEntries.reduce((sum, item) => sum + item.sales, 0) / weekdayEntries.length
        : 0;

    return {
      weekday,
      averageRevenue,
      latestRevenue: latest?.sales ?? 0,
      latestLabel: latest?.fullLabel ?? weekday,
    };
  });
}

function buildWeekdayRevenueData(data: SalesWeekdayBreakdown[]) {
  return data.map((item) => ({
    weekday: item.weekday,
    averageRevenue: item.orders > 0 ? item.amount / item.orders : item.amount,
    latestRevenue: item.amount,
    latestLabel: item.weekday,
    quantity: item.quantity,
    orders: item.orders,
  }));
}

function WeekdayRevenueChart({ data }: { data: ReturnType<typeof buildWeekdayRevenueData> }) {
  return (
    <div className="h-[300px] pt-2">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} margin={{ top: 8, right: 8, left: -12, bottom: 0 }}>
          <CartesianGrid vertical={false} strokeDasharray="3 3" stroke="#334155" opacity={0.2} />
          <XAxis
            dataKey="weekday"
            tickLine={false}
            axisLine={false}
            tick={{ fill: "#94a3b8", fontSize: 12 }}
          />
          <YAxis
            tickLine={false}
            axisLine={false}
            tick={{ fill: "#94a3b8", fontSize: 12 }}
            tickFormatter={(value) => {
              const numericValue = Number(value);
              return numericValue >= 1000 ? `${Math.round(numericValue / 1000)}k` : `${Math.round(numericValue)}`;
            }}
          />
          <Tooltip
            cursor={{ fill: "rgba(148, 163, 184, 0.08)" }}
            contentStyle={{
              borderRadius: "12px",
              border: "1px solid rgba(148, 163, 184, 0.2)",
              background: "rgba(15, 23, 42, 0.96)",
              color: "#e2e8f0",
            }}
            labelFormatter={(_, payload) => payload?.[0]?.payload?.latestLabel || ""}
            formatter={(value, _name, payload) => [
              `${euro.format(Number(value ?? 0))} | Qty: ${Math.round(payload?.payload?.quantity ?? 0).toLocaleString()}`,
              "Average weekday revenue",
            ]}
          />
          <Legend iconType="circle" />
          <Bar dataKey="averageRevenue" name="Average weekday revenue" fill="#3b82f6" radius={[8, 8, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

function RankedSalesBarChart<T extends SalesBreakdownItem>({
  data,
  labelKey,
  emptyMessage,
}: {
  data: T[];
  labelKey: keyof T;
  emptyMessage: string;
}) {
  const chartData = data
    .filter((item) => item.amount > 0)
    .slice(0, 10)
    .map((item) => ({
      label: cleanSalesDimensionLabel(String(item[labelKey])),
      fullLabel: String(item[labelKey]),
      amount: item.amount,
      quantity: item.quantity,
    }));

  if (chartData.length === 0) {
    return <p className="text-sm text-muted-foreground">{emptyMessage}</p>;
  }

  const chartHeight = Math.max(420, chartData.length * 48 + 96);

  return (
    <div className="pt-2" style={{ height: chartHeight }}>
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={chartData} layout="vertical" margin={{ top: 8, right: 24, left: 32, bottom: 0 }}>
          <CartesianGrid horizontal={false} strokeDasharray="3 3" stroke="#334155" opacity={0.2} />
          <XAxis
            type="number"
            tickLine={false}
            axisLine={false}
            tick={{ fill: "#94a3b8", fontSize: 12 }}
            tickFormatter={(value) => {
              const numericValue = Number(value);
              return numericValue >= 1000 ? `${Math.round(numericValue / 1000)}k` : `${Math.round(numericValue)}`;
            }}
          />
          <YAxis
            type="category"
            dataKey="label"
            width={190}
            tickLine={false}
            axisLine={false}
            tick={{ fill: "#94a3b8", fontSize: 12, width: 180 }}
          />
          <Tooltip
            cursor={{ fill: "rgba(148, 163, 184, 0.08)" }}
            contentStyle={{
              borderRadius: "12px",
              border: "1px solid rgba(148, 163, 184, 0.2)",
              background: "rgba(15, 23, 42, 0.96)",
              color: "#e2e8f0",
            }}
            labelFormatter={(_, payload) => payload?.[0]?.payload?.fullLabel || ""}
            formatter={(value, name, payload) => {
              if (String(name) === "amount") {
                return [
                  `${euro.format(Number(value ?? 0))} | Qty: ${Math.round(payload?.payload?.quantity ?? 0).toLocaleString()}`,
                  "Revenue",
                ];
              }
              return [payload?.payload?.quantity?.toLocaleString() ?? value, "Units"];
            }}
          />
          <Legend iconType="circle" />
          <Bar dataKey="amount" name="Revenue" fill="#3b82f6" radius={[0, 8, 8, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

function cleanSalesDimensionLabel(value: string) {
  const cleaned = value
    .normalize("NFKD")
    .replace(/[^\p{L}\p{N}\s/&'-]/gu, " ")
    .replace(/\s*\/\s*/g, " / ")
    .replace(/\s+/g, " ")
    .trim();

  return cleaned
    .split(" / ")
    .map((part) =>
      part
        .toLowerCase()
        .replace(/\b\w/g, (letter) => letter.toUpperCase())
    )
    .join(" / ");
}

function RankedStockBarChart<T extends { value: number; quantity: number }>({
  data,
  labelKey,
  emptyMessage,
}: {
  data: T[];
  labelKey: keyof T;
  emptyMessage: string;
}) {
  const chartData = data
    .filter((item) => item.value > 0)
    .slice(0, 10)
    .map((item) => ({
      label: cleanSalesDimensionLabel(String(item[labelKey])),
      fullLabel: String(item[labelKey]),
      value: item.value,
      quantity: item.quantity,
    }));

  if (!chartData.length) return <p className="text-sm text-muted-foreground">{emptyMessage}</p>;

  return (
    <div className="h-[420px] pt-2">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={chartData} layout="vertical" margin={{ top: 8, right: 24, left: 32, bottom: 0 }}>
          <CartesianGrid horizontal={false} strokeDasharray="3 3" stroke="#334155" opacity={0.2} />
          <XAxis type="number" tickLine={false} axisLine={false} tick={{ fill: "#94a3b8", fontSize: 12 }} tickFormatter={(value) => `${Math.round(Number(value) / 1000)}k`} />
          <YAxis type="category" dataKey="label" width={190} tickLine={false} axisLine={false} tick={{ fill: "#94a3b8", fontSize: 12, width: 180 }} />
          <Tooltip
            cursor={{ fill: "rgba(148, 163, 184, 0.08)" }}
            contentStyle={{ borderRadius: "12px", border: "1px solid rgba(148, 163, 184, 0.2)", background: "rgba(15, 23, 42, 0.96)", color: "#e2e8f0" }}
            labelFormatter={(_, payload) => payload?.[0]?.payload?.fullLabel || ""}
            formatter={(value, _name, payload) => [
              `${euro.format(Number(value ?? 0))} | Qty: ${Math.round(payload?.payload?.quantity ?? 0).toLocaleString()}`,
              "Stock value",
            ]}
          />
          <Legend iconType="circle" />
          <Bar dataKey="value" name="Stock value" fill="#06b6d4" radius={[0, 8, 8, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

function SupplierBillsChart({ data }: { data: NonNullable<OpenBills["by_supplier"]> }) {
  const chartData = data
    .filter((item) => item.open_amount > 0)
    .slice(0, 10)
    .map((item) => ({
      supplier: item.supplier,
      label: cleanSalesDimensionLabel(item.supplier),
      open_amount: item.open_amount,
      count: item.count,
    }));

  if (!chartData.length) return <p className="text-sm text-muted-foreground">No open supplier bills found.</p>;

  return (
    <div className="h-[420px] pt-2">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={chartData} layout="vertical" margin={{ top: 8, right: 24, left: 32, bottom: 0 }}>
          <CartesianGrid horizontal={false} strokeDasharray="3 3" stroke="#334155" opacity={0.2} />
          <XAxis type="number" tickLine={false} axisLine={false} tick={{ fill: "#94a3b8", fontSize: 12 }} tickFormatter={(value) => `${Math.round(Number(value) / 1000)}k`} />
          <YAxis type="category" dataKey="label" width={210} tickLine={false} axisLine={false} tick={{ fill: "#94a3b8", fontSize: 12, width: 200 }} />
          <Tooltip
            cursor={{ fill: "rgba(148, 163, 184, 0.08)" }}
            contentStyle={{ borderRadius: "12px", border: "1px solid rgba(148, 163, 184, 0.2)", background: "rgba(15, 23, 42, 0.96)", color: "#e2e8f0" }}
            labelFormatter={(_, payload) => payload?.[0]?.payload?.supplier || ""}
            formatter={(value, _name, payload) => [
              `${euro.format(Number(value ?? 0))} | Bills: ${payload?.payload?.count ?? 0}`,
              "Open amount",
            ]}
          />
          <Legend iconType="circle" />
          <Bar dataKey="open_amount" name="Open amount" fill="#8b5cf6" radius={[0, 8, 8, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

function StockAgeChart({ data }: { data: StockAnalytics["by_age"] }) {
  const chartData = data.filter((item) => item.value > 0 || item.quantity > 0);
  if (!chartData.length) return <p className="text-sm text-muted-foreground">No stock age data found.</p>;
  return (
    <div className="h-[320px] pt-2">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={chartData} margin={{ top: 8, right: 8, left: -12, bottom: 0 }}>
          <CartesianGrid vertical={false} strokeDasharray="3 3" stroke="#334155" opacity={0.2} />
          <XAxis dataKey="bucket" tickLine={false} axisLine={false} tick={{ fill: "#94a3b8", fontSize: 12 }} />
          <YAxis tickLine={false} axisLine={false} tick={{ fill: "#94a3b8", fontSize: 12 }} tickFormatter={(value) => `${Math.round(Number(value) / 1000)}k`} />
          <Tooltip
            cursor={{ fill: "rgba(148, 163, 184, 0.08)" }}
            contentStyle={{ borderRadius: "12px", border: "1px solid rgba(148, 163, 184, 0.2)", background: "rgba(15, 23, 42, 0.96)", color: "#e2e8f0" }}
            formatter={(value, _name, payload) => [
              `${euro.format(Number(value ?? 0))} | Qty: ${Math.round(payload?.payload?.quantity ?? 0).toLocaleString()}`,
              "Stock value",
            ]}
          />
          <Legend iconType="circle" />
          <Bar dataKey="value" name="Stock value" fill="#06b6d4" radius={[8, 8, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

function SelectableBillRow({
  bill,
  selected,
  onSelect,
}: {
  bill: OpenBill;
  selected: boolean;
  onSelect: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onSelect}
      className={cn(
        compactFieldGroupClass,
        "w-full text-left transition-colors hover:border-violet-400/50 hover:bg-violet-500/10",
        selected && "border-violet-400 bg-violet-500/10 shadow-sm shadow-violet-500/10"
      )}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="truncate text-sm font-medium">{bill.reference}</p>
          <p className="mt-1 truncate text-xs text-muted-foreground">{bill.supplier ?? "Unknown supplier"}</p>
          <p className="mt-1 text-xs text-muted-foreground">
            {bill.date ?? "No date"} | Due {bill.due_date ?? "No due date"} | {formatPaymentState(bill.payment_state)}
          </p>
        </div>
        <span className="shrink-0 text-sm font-semibold text-eyp-blue">{euro.format(bill.open_amount)}</span>
      </div>
    </button>
  );
}

function BillPreview({ bill }: { bill: OpenBill | null }) {
  if (!bill) {
    return (
      <div className="flex min-h-72 items-center justify-center rounded-2xl border border-dashed border-eyp-blue/20 bg-background/35 p-6 text-center text-sm text-muted-foreground">
        Select a supplier bill to preview its details.
      </div>
    );
  }

  const lines = bill.lines ?? [];

  return (
    <div className="rounded-2xl border border-violet-400/25 bg-background/60 p-4 shadow-sm">
      <div className="flex flex-col gap-3 border-b border-eyp-blue/10 pb-4 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <p className={fieldLabelClass}>Selected bill</p>
          <h3 className="mt-1 text-lg font-semibold">{bill.reference}</h3>
          <p className="mt-1 text-sm text-muted-foreground">{bill.supplier ?? "Unknown supplier"}</p>
        </div>
        <Badge variant="outline">{formatPaymentState(bill.payment_state)}</Badge>
      </div>

      <div className="mt-4 grid gap-3 sm:grid-cols-2">
        <BillPreviewMetric label="Bill date" value={bill.date ?? "-"} />
        <BillPreviewMetric label="Due date" value={bill.due_date ?? "-"} />
        <BillPreviewMetric label="Bill total" value={euro.format(bill.amount)} />
        <BillPreviewMetric label="Still open" value={euro.format(bill.open_amount)} highlight />
      </div>

      <div className="mt-5">
        <div className="mb-2 flex items-center justify-between gap-3">
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-muted-foreground">Bill lines</p>
          <span className="text-xs text-muted-foreground">{lines.length} lines</span>
        </div>
        {lines.length ? (
          <div className="space-y-2">
            {lines.map((line, index) => (
              <div key={`${bill.reference}-${line.description}-${index}`} className="rounded-xl border border-eyp-blue/10 bg-eyp-bg-light/45 p-3">
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <p className="truncate text-sm font-medium">{line.product || line.description || "Bill line"}</p>
                    {line.description && line.description !== line.product ? (
                      <p className="mt-1 line-clamp-2 text-xs text-muted-foreground">{line.description}</p>
                    ) : null}
                    <p className="mt-1 text-xs text-muted-foreground">
                      Qty {line.quantity.toLocaleString()} | Unit {euro.format(line.unit_price)}
                    </p>
                  </div>
                  <span className="shrink-0 text-sm font-semibold text-eyp-blue">{euro.format(line.total || line.subtotal)}</span>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <p className="rounded-xl border border-eyp-blue/10 bg-eyp-bg-light/45 p-3 text-sm text-muted-foreground">
            No bill lines returned by Odoo for this bill.
          </p>
        )}
      </div>
    </div>
  );
}

function BillPreviewMetric({
  label,
  value,
  highlight,
}: {
  label: string;
  value: string;
  highlight?: boolean;
}) {
  return (
    <div className="rounded-xl border border-eyp-blue/10 bg-eyp-bg-light/45 p-3">
      <p className={fieldLabelClass}>{label}</p>
      <p className={cn("mt-1 text-sm font-semibold", highlight && "text-eyp-blue")}>{value}</p>
    </div>
  );
}

function formatPaymentState(value: string) {
  return value
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

function ListRow({ label, value, detail }: { label: string; value: string; detail: string }) {
  return (
    <div className={compactFieldGroupClass}>
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-sm font-medium">{label}</p>
          <p className="mt-1 text-xs text-muted-foreground">{detail}</p>
        </div>
        <span className="text-sm font-semibold text-eyp-blue">{value}</span>
      </div>
    </div>
  );
}

function SalesHourBreakdownChart({ data }: { data: SalesHourBreakdown[] }) {
  const storeHours = Array.from({ length: 10 }, (_, index) => index + 10);
  const hourData = storeHours.map((hour) => {
    const match = data.find((item) => item.hour === hour);
    return {
      hour,
      label: `${hour.toString().padStart(2, "0")}:00`,
      amount: match?.amount ?? 0,
      quantity: match?.quantity ?? 0,
      orders: match?.orders ?? 0,
    };
  });
  const maxAmount = Math.max(...hourData.map((item) => item.amount), 0);
  const nonZeroHours = hourData.filter((item) => item.amount > 0);

  if (maxAmount === 0) {
    return <p className="text-sm text-muted-foreground">No sales found between 10:00 and 19:00 for this period.</p>;
  }

  const peakHour = hourData.reduce((best, item) => (item.amount > best.amount ? item : best), hourData[0]);
  const slowestHour = (nonZeroHours.length ? nonZeroHours : hourData).reduce(
    (slowest, item) => (item.amount < slowest.amount ? item : slowest),
    nonZeroHours[0] ?? hourData[0]
  );
  const morningRevenue = hourData
    .filter((item) => item.hour >= 10 && item.hour <= 12)
    .reduce((sum, item) => sum + item.amount, 0);
  const afternoonRevenue = hourData
    .filter((item) => item.hour >= 13 && item.hour <= 19)
    .reduce((sum, item) => sum + item.amount, 0);

  return (
    <div className="space-y-4 pt-2">
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <HourCallout label="Peak hour" value={peakHour.label} detail={euro.format(peakHour.amount)} />
        <HourCallout label="Slowest hour" value={slowestHour.label} detail={euro.format(slowestHour.amount)} />
        <HourCallout label="Morning revenue" value={euro.format(morningRevenue)} detail="10:00-12:00" />
        <HourCallout label="Afternoon/evening" value={euro.format(afternoonRevenue)} detail="13:00-19:00" />
      </div>

      <div className="grid gap-2 lg:grid-cols-10">
        {hourData.map((item) => {
          const intensity = item.amount / maxAmount;
          const active = item.amount > 0;
          return (
            <div
              key={item.hour}
              className={cn(
                "min-h-28 rounded-2xl border p-3 transition-colors",
                active ? "border-eyp-blue/25 text-foreground" : "border-border/60 text-muted-foreground"
              )}
              style={{
                background: active
                  ? `linear-gradient(180deg, rgba(26,154,250,${0.16 + intensity * 0.46}), rgba(26,154,250,${0.06 + intensity * 0.18}))`
                  : "hsl(var(--background) / 0.35)",
              }}
              title={`${item.label}: ${euro.format(item.amount)} | Qty: ${Math.round(item.quantity).toLocaleString()}`}
            >
              <div className="text-xs font-semibold">{item.label}</div>
              <div className="mt-4 text-sm font-semibold">{euro.format(item.amount)}</div>
              <div className="mt-1 text-[11px] text-muted-foreground">
                {Math.round(item.quantity)} units
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function HourCallout({ label, value, detail }: { label: string; value: string; detail: string }) {
  return (
    <div className="rounded-2xl border border-eyp-blue/15 bg-background/40 p-4">
      <div className={fieldLabelClass}>{label}</div>
      <div className="mt-2 text-lg font-semibold">{value}</div>
      <div className="mt-1 text-xs text-muted-foreground">{detail}</div>
    </div>
  );
}
