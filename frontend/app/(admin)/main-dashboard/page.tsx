"use client";

import { useQuery } from "@tanstack/react-query";
import { clientFetch } from "@/lib/client-fetch";
import { Zap, Users, RefreshCw } from "lucide-react";
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
  const history = data?.credit_usage_history ?? [];
  const chartData = history.map((d: any) => d.total);

  const chartMax = Math.max(...chartData, 1);

  return (
    <div className={styles.page}>
      {/* Header */}
      <header className={styles.header}>
        <div className={styles.header_text}>
          <p className={styles.eyebrow}>ADMIN CONSOLE</p>
          <h1 className={styles.title}>Overview Dashboard</h1>
          <p className={styles.subtitle}>
            System-wide credit usage & analytics
          </p>
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

      {/* KPI Row — only 2 real stats */}
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

      {/* Credit Usage Chart — full width */}
      <div className={styles.chartCard}>
        <div className={styles.chartHead}>
          <div>
            <p className={styles.chartLabel}>Credits Usage History</p>
            <p className={styles.chartSub}>Last 7 days</p>
          </div>
          <div className={styles.chartBadge}>LIVE</div>
        </div>

        <div className={styles.chartArea}>
          {/* Y axis labels */}
          <div className={styles.yAxis}>
            {[chartMax, Math.round(chartMax / 2), 0].map((v, i) => (
              <span key={`${v}-${i}`} className={styles.yLabel}>
                {fmt(v)}
              </span>
            ))}
          </div>

          {/* Bars */}
          <div className={styles.bars}>
            {chartData.map((val: number, i: number) => {
              const pct = chartMax > 0 ? (val / chartMax) * 100 : 0;
              return (
                <div key={i} className={styles.barCol}>
                  <div className={styles.barTrack}>
                    <div
                      className={styles.barFill}
                      style={{ height: `${pct}%` }}
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

        <div className={styles.chartFooter}>
          <div className={styles.chartStat}>
            <span className={styles.chartStatLabel}>PEAK</span>
            <span className={styles.chartStatVal} style={{ color: "#3b82f6" }}>
              {fmt(Math.max(...chartData, 0))} Credits
            </span>
          </div>
          <div className={styles.chartDivider} />
          <div className={styles.chartStat}>
            <span className={styles.chartStatLabel}>DAILY AVG</span>
            <span className={styles.chartStatVal} style={{ color: "#a78bfa" }}>
              {fmt(
                chartData.length
                  ? Math.round(
                      chartData.reduce((a: number, b: number) => a + b, 0) /
                        chartData.length,
                    )
                  : 0,
              )}{" "}
              Credits
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
