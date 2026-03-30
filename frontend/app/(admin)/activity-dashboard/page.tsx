"use client";

import { useQuery } from "@tanstack/react-query";
import { clientFetch } from "@/lib/client-fetch";
import {
  RefreshCw,
  Search,
  Filter,
  ChevronLeft,
  ChevronRight,
  Film,
  ScanSearch,
  Zap,
  CircleDot,
  Clock,
} from "lucide-react";
import { useState } from "react";
import styles from "./page.module.css";

type LogType = "all" | "topup" | "analysis_lock" | "generation_lock" | "refund";
type StatusFilter = "all" | "completed" | "processing" | "failed";

interface ActivityItem {
  id: number;
  date_time: string;
  username: string;
  activate: string;
  details: string;
  credits: number;
  status: "completed" | "processing" | "failed";
  type: string;
}

const fetchActivity = async (
  page: number,
  typeFilter: string,
  status: string,
) => {
  const params = new URLSearchParams({
    page: String(page),
    type: typeFilter,
    status,
  });
  const res = await clientFetch(`/api/admin/activity-dashboard?${params}`);
  if (!res.ok) throw new Error("Failed");
  return res.json();
};

const STATUS_MAP = {
  completed: {
    label: "Completed",
    color: "#10b981",
    bg: "rgba(16,185,129,0.1)",
    border: "rgba(16,185,129,0.25)",
  },
  processing: {
    label: "Processing",
    color: "#3b82f6",
    bg: "rgba(59,130,246,0.1)",
    border: "rgba(59,130,246,0.25)",
  },
  failed: {
    label: "Failed",
    color: "#ef4444",
    bg: "rgba(239,68,68,0.1)",
    border: "rgba(239,68,68,0.25)",
  },
};

const TYPE_ICONS: Record<string, React.ElementType> = {
  Generate: Film,
  Analyze: ScanSearch,
  Topup: Zap,
  Refund: CircleDot,
};
const TYPE_COLORS: Record<string, string> = {
  Generate: "#3b82f6",
  Analyze: "#10b981",
  Topup: "#f59e0b",
  Refund: "#a78bfa",
};

export default function ActivityDashboard() {
  const [page, setPage] = useState(1);
  const [typeFilter, setTypeFilter] = useState<LogType>("all");
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("all");
  const [search, setSearch] = useState("");

  const { data, isLoading, refetch, isFetching } = useQuery({
    queryKey: ["admin-activity", page, typeFilter, statusFilter],
    queryFn: () => fetchActivity(page, typeFilter, statusFilter),
    refetchInterval: 15_000,
  });

  const items: ActivityItem[] = data?.results ?? [];
  const totalPages = data?.total_pages ?? 1;
  const totalCount = data?.total_count ?? 0;
  const summaryStats = data?.summary ?? {
    total_analysis: 0,
    total_generation: 0,
    total_topup: 0,
    total_refund: 0,
  };

  const filtered = search
    ? items.filter(
        (i) =>
          i.username?.toLowerCase().includes(search.toLowerCase()) ||
          i.details?.toLowerCase().includes(search.toLowerCase()),
      )
    : items;

  const formatDate = (d: string) =>
    d
      ? new Date(d).toLocaleString("th-TH", {
          day: "2-digit",
          month: "short",
          year: "2-digit",
          hour: "2-digit",
          minute: "2-digit",
        })
      : "—";

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <div className={styles.header_text}>
          <p className={styles.eyebrow}>ADMIN CONSOLE</p>
          <h1 className={styles.title}>Activity Dashboard</h1>
          <p className={styles.subtitle}>
            All credit transactions & system events
          </p>
        </div>
        <div className={styles.header_button}>
          <button
            className={`${styles.refreshBtn} ${isFetching ? styles.spinning : ""}`}
            onClick={() => refetch()}
          >
            <RefreshCw size={14} /> Refresh
          </button>
        </div>
      </header>
      <div className={styles.summaryRow}>
        {[
          {
            label: "Analysis",
            val: summaryStats.total_analysis,
            color: "#10b981",
            icon: ScanSearch,
          },
          {
            label: "Generation",
            val: summaryStats.total_generation,
            color: "#3b82f6",
            icon: Film,
          },
          {
            label: "Top-up",
            val: summaryStats.total_topup,
            color: "#f59e0b",
            icon: Zap,
          },
          {
            label: "Refund",
            val: summaryStats.total_refund,
            color: "#a78bfa",
            icon: CircleDot,
          },
        ].map(({ label, val, color, icon: Icon }) => (
          <div key={label} className={styles.summaryChip}>
            <div
              className={styles.summaryIcon}
              style={{ color, background: `${color}18` }}
            >
              <Icon size={13} />
            </div>
            <span className={styles.summaryLabel}>{label}</span>
            <span className={styles.summaryVal} style={{ color }}>
              {isLoading ? "—" : val}
            </span>
          </div>
        ))}
      </div>

      <div className={styles.tableCard}>
        <div className={styles.filterBar}>
          <div className={styles.searchBox}>
            <Search size={13} className={styles.searchIcon} />
            <input
              className={styles.searchInput}
              placeholder="Search user or session…"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </div>
          <div className={styles.filters}>
            <Filter size={13} style={{ color: "rgba(226,232,248,0.3)" }} />
            <select
              className={styles.select}
              value={typeFilter}
              onChange={(e) => {
                setTypeFilter(e.target.value as LogType);
                setPage(1);
              }}
            >
              <option value="all">All Types</option>
              <option value="analysis_lock">Analysis</option>
              <option value="generation_lock">Generation</option>
              <option value="topup">Top-up</option>
              <option value="refund">Refund</option>
            </select>
            <select
              className={styles.select}
              value={statusFilter}
              onChange={(e) => {
                setStatusFilter(e.target.value as StatusFilter);
                setPage(1);
              }}
            >
              <option value="all">All Status</option>
              <option value="completed">Completed</option>
              <option value="processing">Processing</option>
              <option value="failed">Failed</option>
            </select>
          </div>
        </div>

        <div className={styles.tableWrap}>
          <table className={styles.table}>
            <thead>
              <tr>
                {[
                  "TX ID",
                  "User",
                  "Type",
                  "Session / Detail",
                  "Credits",
                  "Status",
                  "Date",
                ].map((h) => (
                  <th key={h} className={styles.th}>
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {isLoading
                ? Array(8)
                    .fill(null)
                    .map((_, i) => (
                      <tr key={i} className={styles.tr}>
                        {Array(7)
                          .fill(null)
                          .map((_, j) => (
                            <td key={j} className={styles.td}>
                              <div className={styles.skeleton} />
                            </td>
                          ))}
                      </tr>
                    ))
                : filtered.map((item) => {
                    const TypeIcon = TYPE_ICONS[item.activate] ?? Clock;
                    const typeColor = TYPE_COLORS[item.activate] ?? "#888";
                    const statusCfg =
                      STATUS_MAP[item.status] ?? STATUS_MAP.completed;
                    const isPositive = item.credits >= 0;

                    return (
                      <tr key={item.id} className={styles.tr}>
                        <td className={styles.td}>
                          <span className={styles.txId}>#{item.id}</span>
                        </td>
                        <td className={styles.td}>
                          <span className={styles.username}>
                            {item.username ?? "—"}
                          </span>
                        </td>
                        <td className={styles.td}>
                          <span
                            className={styles.typeBadge}
                            style={{
                              color: typeColor,
                              background: `${typeColor}15`,
                              borderColor: `${typeColor}30`,
                            }}
                          >
                            <TypeIcon size={10} />
                            {item.activate}
                          </span>
                        </td>
                        <td className={styles.td}>
                          <span className={styles.details}>{item.details}</span>
                        </td>
                        <td className={styles.td}>
                          <span
                            className={styles.credits}
                            style={{
                              color: isPositive ? "#86efac" : "#fca5a5",
                            }}
                          >
                            {isPositive ? "+" : "−"}
                            {Math.abs(Number(item.credits))}
                          </span>
                        </td>
                        <td className={styles.td}>
                          <span
                            className={styles.statusChip}
                            style={{
                              color: statusCfg.color,
                              background: statusCfg.bg,
                              borderColor: statusCfg.border,
                            }}
                          >
                            <span
                              className={`${styles.statusDot} ${item.status === "processing" ? styles.dotPulse : ""}`}
                              style={{ background: statusCfg.color }}
                            />
                            {statusCfg.label}
                          </span>
                        </td>
                        <td className={styles.td}>
                          <span className={styles.dateText}>
                            {formatDate(item.date_time)}
                          </span>
                        </td>
                      </tr>
                    );
                  })}
            </tbody>
          </table>
        </div>

        <div className={styles.pagination}>
          <span className={styles.pageInfo}>
            {totalCount} records · page {page} of {totalPages}
          </span>
          <div className={styles.pageButtons}>
            <button
              className={styles.pageBtn}
              disabled={page <= 1}
              onClick={() => setPage((p) => p - 1)}
            >
              <ChevronLeft size={14} />
            </button>
            <span className={styles.pageCurrent}>{page}</span>
            <button
              className={styles.pageBtn}
              disabled={page >= totalPages}
              onClick={() => setPage((p) => p + 1)}
            >
              <ChevronRight size={14} />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
