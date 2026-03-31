"use client";

import { useQuery } from "@tanstack/react-query";
import { clientFetch } from "@/lib/client-fetch";
import { Zap, Users, RefreshCw, DollarSign } from "lucide-react"; // เพิ่ม DollarSign
import styles from "./page.module.css";

/* ── API ── */
const fetchMainDashboard = async () => {
  const res = await clientFetch("/api/admin/main-dashboard");
  if (!res.ok) throw new Error("Failed");
  return res.json();
};

/* ── HELPERS ── */
const fmt = (n: number) =>
  n >= 1000 ? `${(n / 1000).toFixed(1)}K` : String(n);

const DAYS = ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"];

export default function MainDashboard() {
  const { data, isLoading, refetch, isFetching } = useQuery({
    queryKey: ["admin-main"],
    queryFn: fetchMainDashboard,
    refetchInterval: 30_000,
  });

  const stats = data?.stats ?? {};
  const creditHistory = data?.credit_usage_history ?? [];
  const incomesHistory = data?.incomes_history ?? [];

  const chartCreditData = creditHistory.map((d: any) => d.total);
  const chartIncomeData = incomesHistory.map((d: any) => d.total);

  const chartCreditMax = Math.max(...chartCreditData, 1);
  const chartIncomeMax = Math.max(...chartIncomeData, 1);

  return (
    <div className={styles.page}>
      {/* Header */}
      <header className={styles.header}>
        <div className={styles.header_text}>
          <p className={styles.eyebrow}>ADMIN CONSOLE</p>
          <h1 className={styles.title}>Overview Dashboard</h1>
          <p className={styles.subtitle}>System-wide analytics & revenue</p>
        </div>
        <div className={styles.header_button}>
          <button
            className={`${styles.refreshBtn} ${isFetching ? styles.spinning : ""}`}
            onClick={() => refetch()}
          >
            <RefreshCw size={14} />
            Refresh
          </button>
        </div>
      </header>

      {/* KPI Row — 3 stats now */}
      <div className={styles.kpiGrid}>
        {[
          {
            icon: Zap,
            color: "#3b82f6",
            bg: "rgba(59,130,246,0.1)",
            label: "Total Credits Used",
            value: fmt(stats.total_credits_used ?? 0),
            sub: "All time",
          },
          {
            icon: DollarSign,
            color: "#f59e0b",
            bg: "rgba(245,158,11,0.1)",
            label: "Total Incomes",
            value: `฿${fmt(stats.total_incomes ?? 0)}`,
            sub: "Gross Revenue",
          },
          {
            icon: Users,
            color: "#10b981",
            bg: "rgba(16,185,129,0.1)",
            label: "Active Users",
            value: fmt(stats.active_users ?? 0),
            sub: "With sessions",
          },
        ].map(({ icon: Icon, color, bg, label, value, sub }) => (
          <div key={label} className={styles.kpiCard}>
            <div className={styles.kpiIcon} style={{ background: bg, color }}>
              <Icon size={18} />
            </div>
            <div>
              <p className={styles.kpiLabel}>{label}</p>
              <p className={styles.kpiValue}>{isLoading ? "—" : value}</p>
              <p className={styles.kpiSub}>{sub}</p>
            </div>
          </div>
        ))}
      </div>

      {/* --- Charts Section --- */}
      <div className={styles.chartsStack}>
        {/* 1. Credit Usage Chart */}
        <div className={styles.chartCard}>
          <div className={styles.chartHead}>
            <div>
              <p className={styles.chartLabel}>Credits Usage History</p>
              <p className={styles.chartSub}>Last 7 days usage</p>
            </div>
            <div className={`${styles.chartBadge} ${styles.blueBadge}`}>
              LIVE
            </div>
          </div>

          <div className={styles.chartArea}>
            <div className={styles.yAxis}>
              {[chartCreditMax, Math.round(chartCreditMax / 2), 0].map(
                (v, i) => (
                  <span key={i} className={styles.yLabel}>
                    {fmt(v)}
                  </span>
                ),
              )}
            </div>
            <div className={styles.bars}>
              {chartCreditData.map((val: number, i: number) => {
                const pct = (val / chartCreditMax) * 100;
                return (
                  <div key={i} className={styles.barCol}>
                    <div className={styles.barTrack}>
                      <div
                        className={styles.barFill}
                        style={{ height: `${pct}%`, background: "#3b82f6" }}
                      >
                        <div className={styles.barGlow} />
                      </div>
                    </div>
                    <span className={styles.barDay}>{DAYS[i]}</span>
                  </div>
                );
              })}
            </div>
          </div>
        </div>

        {/* 2. Incomes History Chart */}
        <div className={styles.chartCard}>
          <div className={styles.chartHead}>
            <div>
              <p className={styles.chartLabel}>Incomes History</p>
              <p className={styles.chartSub}>Last 7 days revenue</p>
            </div>
            <div className={`${styles.chartBadge} ${styles.goldBadge}`}>
              REVENUE
            </div>
          </div>

          <div className={styles.chartArea}>
            <div className={styles.yAxis}>
              {[chartIncomeMax, Math.round(chartIncomeMax / 2), 0].map(
                (v, i) => (
                  <span key={i} className={styles.yLabel}>
                    {fmt(v)}
                  </span>
                ),
              )}
            </div>
            <div className={styles.bars}>
              {chartIncomeData.map((val: number, i: number) => {
                const pct = (val / chartIncomeMax) * 100;
                return (
                  <div key={i} className={styles.barCol}>
                    <div className={styles.barTrack}>
                      <div
                        className={styles.barFill}
                        style={{ height: `${pct}%`, background: "#f59e0b" }}
                      >
                        <div
                          className={styles.barGlow}
                          style={{ background: "rgba(245,158,11,0.5)" }}
                        />
                      </div>
                    </div>
                    <span className={styles.barDay}>{DAYS[i]}</span>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
