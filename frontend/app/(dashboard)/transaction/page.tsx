"use client";

import { useEffect, useState } from "react";
import { clientFetch } from "@/lib/client-fetch";
import {
  CreditCard,
  Zap,
  ArrowDownLeft,
  ArrowUpRight,
  ChevronLeft,
  ChevronRight,
  ArrowUpDown,
} from "lucide-react";
import styles from "./page.module.css";

interface Billing {
  id: number;
  date_time: string;
  package: string;
  amount: string;
  status: string;
}

interface Activity {
  id: number;
  date_time: string;
  activate: string;
  details: string;
  credits: string;
  status: string;
}

const PAGE_SIZE = 50;

const STATUS_LABEL: Record<string, string> = {
  pending: "Pending",
  success: "Success",
  completed: "Completed",
  failed: "Failed",
  processing: "Processing",
};

const ACTION_ICON: Record<string, React.ReactNode> = {
  Topup: <ArrowDownLeft size={13} />,
  Analyze: <Zap size={13} />,
  Generate: <Zap size={13} />,
  Refund: <ArrowUpRight size={13} />,
};

export default function TransactionPage() {
  const [activeTab, setActiveTab] = useState<"billing" | "activity">("billing");
  const [data, setData] = useState<Billing[] | Activity[]>([]);
  const [loading, setLoading] = useState(true);
  const [sortOrder, setSortOrder] = useState<"desc" | "asc">("desc");
  const [page, setPage] = useState(1);

  const fetchData = async (type: "billing" | "activity") => {
    setLoading(true);
    try {
      const res = await clientFetch(`/api/transaction?type=${type}`);
      const result = await res.json();
      setData(result);
    } catch (err) {
      console.error("Fetch error:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData(activeTab);
    setPage(1);
  }, [activeTab]);

  // Reset page when sort changes
  useEffect(() => {
    setPage(1);
  }, [sortOrder]);

  const formatDate = (date: string) => {
    const d = new Date(date);
    return {
      date: d.toLocaleDateString("en-US", {
        month: "short",
        day: "2-digit",
        year: "numeric",
      }),
      time: d.toLocaleTimeString("en-US", {
        hour: "2-digit",
        minute: "2-digit",
      }),
    };
  };

  const sortedData = [...data].sort((a, b) => {
    const tA = new Date(a.date_time).getTime();
    const tB = new Date(b.date_time).getTime();
    return sortOrder === "desc" ? tB - tA : tA - tB;
  });

  const totalPages = Math.max(1, Math.ceil(sortedData.length / PAGE_SIZE));
  const pagedData = sortedData.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);

  const toggleSort = () =>
    setSortOrder((prev) => (prev === "desc" ? "asc" : "desc"));

  // ── Loading: rendered OUTSIDE container, same pattern as Library ──
  if (loading)
    return (
      <div className={styles.loadingState}>
        <div className={styles.loadingBar}>
          <div className={styles.loadingFill} />
        </div>
        <span>Loading Records…</span>
      </div>
    );

  return (
    <div className={styles.container}>
      {/* ── Header ── */}
      <header className={styles.header}>
        <div className={styles.headerLeft}>
          <div className={styles.headerIcon}>
            <CreditCard size={18} />
          </div>
          <div>
            <h1 className={styles.title}>Billing & Activity</h1>
            <p className={styles.subtitle}>Payment history and credit usage</p>
          </div>
        </div>

        {/* Tab switcher */}
        <div className={styles.tabGroup}>
          <button
            className={`${styles.tab} ${activeTab === "billing" ? styles.tabActive : ""}`}
            onClick={() => setActiveTab("billing")}
          >
            <CreditCard size={14} />
            Billing
          </button>
          <button
            className={`${styles.tab} ${activeTab === "activity" ? styles.tabActive : ""}`}
            onClick={() => setActiveTab("activity")}
          >
            <Zap size={14} />
            Activity
          </button>
        </div>
      </header>

      {/* ── Toolbar: Sort + Record count ── */}
      {data.length > 0 && (
        <div className={styles.toolbar}>
          <span className={styles.recordCount}>
            {data.length} record{data.length !== 1 ? "s" : ""}
          </span>
          <button className={styles.sortBtn} onClick={toggleSort}>
            <ArrowUpDown size={13} />
            {sortOrder === "desc" ? "Newest first" : "Oldest first"}
          </button>
        </div>
      )}

      {/* ── Content ── */}
      {data.length === 0 ? (
        <div className={styles.emptyState}>
          <div className={styles.emptyIcon}>
            {activeTab === "billing" ? (
              <CreditCard size={28} />
            ) : (
              <Zap size={28} />
            )}
          </div>
          <p className={styles.emptyTitle}>No records yet</p>
          <p className={styles.emptyDesc}>
            {activeTab === "billing"
              ? "Your payment history will appear here"
              : "Credit usage from AI tasks will appear here"}
          </p>
        </div>
      ) : (
        <>
          <div className={styles.tableWrapper}>
            <table className={styles.table}>
              <thead>
                <tr>
                  <th>Date</th>
                  {activeTab === "billing" ? (
                    <>
                      <th>Package</th>
                      <th>Amount</th>
                      <th>Status</th>
                    </>
                  ) : (
                    <>
                      <th>Action</th>
                      <th>Details</th>
                      <th>Credits</th>
                      <th>Status</th>
                    </>
                  )}
                </tr>
              </thead>

              <tbody>
                {activeTab === "billing"
                  ? (pagedData as Billing[]).map((item, i) => {
                      const { date, time } = formatDate(item.date_time);
                      return (
                        <tr
                          key={item.id}
                          style={{ animationDelay: `${i * 30}ms` }}
                        >
                          <td>
                            <span className={styles.dateMain}>{date}</span>
                            <span className={styles.dateTime}>{time}</span>
                          </td>
                          <td>
                            <span className={styles.packageName}>
                              {item.package}
                            </span>
                          </td>
                          <td>
                            <span className={styles.amount}>
                              ฿{Number(item.amount).toLocaleString()}
                            </span>
                          </td>
                          <td>
                            <span
                              className={`${styles.badge} ${styles[`badge_${item.status}`]}`}
                            >
                              {STATUS_LABEL[item.status] ?? item.status}
                            </span>
                          </td>
                        </tr>
                      );
                    })
                  : (pagedData as Activity[]).map((item, i) => {
                      const { date, time } = formatDate(item.date_time);
                      const isDebit =
                        item.activate !== "Topup" && item.activate !== "Refund";
                      const isFailed = item.status === "failed";
                      return (
                        <tr
                          key={item.id}
                          style={{ animationDelay: `${i * 30}ms` }}
                        >
                          <td>
                            <span className={styles.dateMain}>{date}</span>
                            <span className={styles.dateTime}>{time}</span>
                          </td>
                          <td>
                            <span className={styles.actionCell}>
                              <span
                                className={`${styles.actionIcon} ${styles[`actionIcon_${item.activate?.toLowerCase() ?? ""}`]}`}
                              >
                                {ACTION_ICON[item.activate] ?? (
                                  <Zap size={13} />
                                )}
                              </span>
                              {item.activate ?? "—"}
                            </span>
                          </td>
                          <td>
                            <span className={styles.details}>
                              {item.details}
                            </span>
                          </td>
                          <td>
                            <span
                              className={`${styles.credits} ${
                                isFailed
                                  ? styles.creditsFailed
                                  : isDebit
                                    ? styles.creditsDebit
                                    : styles.creditsCredit
                              }`}
                            >
                              {isFailed
                                ? "—"
                                : isDebit
                                  ? `${Number(item.credits).toLocaleString()}`
                                  : `+${Number(item.credits).toLocaleString()}`}
                            </span>
                          </td>
                          <td>
                            <span
                              className={`${styles.badge} ${styles[`badge_${item.status}`]}`}
                            >
                              {STATUS_LABEL[item.status] ?? item.status}
                            </span>
                          </td>
                        </tr>
                      );
                    })}
              </tbody>
            </table>
          </div>

          {/* ── Pagination ── */}
          {totalPages > 1 && (
            <div className={styles.pagination}>
              <span className={styles.pageInfo}>
                Page {page} of {totalPages}
              </span>
              <div className={styles.pageButtons}>
                <button
                  className={styles.pageBtn}
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                  disabled={page === 1}
                >
                  <ChevronLeft size={14} />
                </button>
                {Array.from({ length: totalPages }, (_, i) => i + 1)
                  .filter(
                    (p) =>
                      p === 1 || p === totalPages || Math.abs(p - page) <= 1,
                  )
                  .reduce<(number | "...")[]>((acc, p, idx, arr) => {
                    if (idx > 0 && p - (arr[idx - 1] as number) > 1)
                      acc.push("...");
                    acc.push(p);
                    return acc;
                  }, [])
                  .map((p, i) =>
                    p === "..." ? (
                      <span
                        key={`ellipsis-${i}`}
                        className={styles.pageEllipsis}
                      >
                        …
                      </span>
                    ) : (
                      <button
                        key={p}
                        className={`${styles.pageBtn} ${page === p ? styles.pageBtnActive : ""}`}
                        onClick={() => setPage(p as number)}
                      >
                        {p}
                      </button>
                    ),
                  )}
                <button
                  className={styles.pageBtn}
                  onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                  disabled={page === totalPages}
                >
                  <ChevronRight size={14} />
                </button>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
