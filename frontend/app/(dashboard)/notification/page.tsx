"use client";

import { useEffect, useState } from "react";
import { clientFetch } from "@/lib/client-fetch";
import { Bell, CheckCircle2, Clock, Info } from "lucide-react";
import styles from "./page.module.css";

interface Notification {
  id: number;
  task_name: string;
  status: string;
  message: string;
  is_read: boolean;
  created_at: string;
  type: "novel" | "session";
  ref_id: number;
}

export default function NotificationPage() {
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchNotifications = async () => {
    try {
      const res = await clientFetch("/api/notification");
      const result = await res.json();
      if (!res.ok) throw new Error(result.detail || "Failed to fetch");

      // เรียงลำดับเอาอันใหม่ล่าสุดขึ้นก่อน (ถ้า backend ยังไม่เรียงมาให้)
      const sorted = (result.notifications || []).sort(
        (a: Notification, b: Notification) =>
          new Date(b.created_at).getTime() - new Date(a.created_at).getTime(),
      );
      setNotifications(sorted);
    } catch (error) {
      console.error("Notification Error:", error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchNotifications();
  }, []);

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleString("th-TH", {
      day: "2-digit",
      month: "short",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  if (loading)
    return <div className={styles.statusText}>Loading Notifications...</div>;

  return (
    <div className={styles.container}>
      <header className={styles.header}>
        <div className={styles.titleGroup}>
          <h1>Notifications</h1>
          <span className={styles.badge}>
            {notifications.filter((n) => !n.is_read).length} Unread
          </span>
        </div>
      </header>

      <div className={styles.list}>
        {notifications.length === 0 ? (
          <div className={styles.emptyState}>
            <Bell size={48} />
            <p>No notifications yet</p>
          </div>
        ) : (
          notifications.map((item) => (
            <div
              key={item.id}
              className={`${styles.card} ${!item.is_read ? styles.unread : ""}`}
            >
              <div className={styles.iconWrapper}>
                {item.status === "processing" ? (
                  <Clock className={styles.statusIconProcessing} size={20} />
                ) : (
                  <CheckCircle2
                    className={styles.statusIconSuccess}
                    size={20}
                  />
                )}
              </div>

              <div className={styles.content}>
                <div className={styles.contentHeader}>
                  <h3 className={styles.taskName}>{item.task_name}</h3>
                  <span className={styles.time}>
                    {formatDate(item.created_at)}
                  </span>
                </div>
                <p className={styles.message}>{item.message}</p>
                <div className={styles.footer}>
                  <span className={styles.typeTag}>#{item.type}</span>
                  {!item.is_read && (
                    <span className={styles.newBadge}>New</span>
                  )}
                </div>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
