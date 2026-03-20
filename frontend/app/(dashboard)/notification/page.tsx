"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { fetchNotifications } from "@/app/services/notification";
import SharePopUpDelete from "@/components/SharePopUp_Delete";
import SharePopUpRetry from "@/components/SharePopUp_Retry";
import { clientFetch } from "@/lib/client-fetch";
import {
  Bell,
  CheckCircle2,
  Clock,
  Trash2,
  RotateCcw,
  AlertCircle,
  Sparkles,
} from "lucide-react";
import styles from "./page.module.css";

export default function NotificationPage() {
  const router = useRouter();
  const queryClient = useQueryClient();

  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [selectedId, setSelectedId] = useState<number | null>(null);

  const [showRetryModal, setShowRetryModal] = useState(false);
  const [retryTarget, setRetryTarget] = useState<{
    notificationId: number;
    sessionId?: number | null;
    novelId?: number | null;
    taskType: string;
    displayName: string;
  } | null>(null);

  const { data: notifications = [], isLoading } = useQuery({
    queryKey: ["notifications"],
    queryFn: fetchNotifications,
    refetchInterval: 5000,
    refetchOnWindowFocus: true,
    refetchIntervalInBackground: false,
  });

  const markReadMutation = useMutation({
    mutationFn: async (id: number) => {
      await clientFetch(`/api/notification/${id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ is_read: true }),
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["notifications"] });
      queryClient.invalidateQueries({
        queryKey: ["notification-unread-count"],
      });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: async (id: number) => {
      await clientFetch(`/api/notification/${id}`, { method: "DELETE" });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["notifications"] });
    },
  });

  const retryMutation = useMutation({
    mutationFn: async () => {
      if (!retryTarget) return;
      const { taskType, notificationId, sessionId, novelId } = retryTarget;
      if (taskType === "upload") {
        await clientFetch(`/api/notification/${notificationId}/retry-upload`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ novel_id: novelId }),
        });
      } else {
        await clientFetch(`/api/sessions/retry/${sessionId}/`, {
          method: "POST",
        });
      }
    },
    onSuccess: () => {
      setShowRetryModal(false);
      setRetryTarget(null);
      queryClient.invalidateQueries({ queryKey: ["notifications"] });
    },
  });

  const handleReadAll = async () => {
    const unread = notifications.filter((n) => !n.is_read);
    await Promise.all(unread.map((n) => markReadMutation.mutateAsync(n.id)));
  };

  const handleViewDetail = (id: number) => {
    router.push(`/notification/${id}`);
  };

  const handleRetryClick = (
    e: React.MouseEvent,
    item: (typeof notifications)[number],
  ) => {
    e.stopPropagation();
    setRetryTarget({
      notificationId: item.id,
      taskType: item.task_type,
      novelId: item.type === "novel" ? item.ref_id : null,
      sessionId: item.type === "session" ? item.ref_id : null,
      displayName: item.novel_title || item.task_type,
    });
    setShowRetryModal(true);
  };

  const handleConfirmDelete = () => {
    if (!selectedId) return;
    deleteMutation.mutate(selectedId, {
      onSuccess: () => {
        setShowDeleteModal(false);
        setSelectedId(null);
      },
    });
  };

  const getRetryWarning = (taskType: string) => {
    if (taskType === "upload") {
      return {
        warningHighlight:
          "การ Retry จะทำการอัปโหลดและประมวลผลไฟล์ใหม่ทั้งหมด บทที่สร้างจากไฟล์เดิมจะถูกลบ แล้วสร้างใหม่จากไฟล์ต้นฉบับ",
      };
    }
    return {
      warningHighlight:
        "การ Retry ไม่ใช่การทำต่อจากการดำเนินงานล่าสุด แต่เป็นการลบการวิเคราะห์เดิมทิ้ง แล้ว สร้างใหม่",
    };
  };

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

  const unreadCount = notifications.filter((n) => !n.is_read).length;

  if (isLoading) {
    return (
      <div className={styles.loadingState}>
        <div className={styles.loadingBar}>
          <div className={styles.loadingFill} />
        </div>
        <span>Loading Notifications…</span>
      </div>
    );
  }

  return (
    <div className={styles.container}>
      {/* Header */}
      <header className={styles.header}>
        <div className={styles.headerLeft}>
          <div className={styles.headerIcon}>
            <Bell size={18} />
          </div>
          <div>
            <h1 className={styles.title}>Notifications</h1>
            <p className={styles.subtitle}>
              {unreadCount > 0
                ? `${unreadCount} unread update${unreadCount > 1 ? "s" : ""}`
                : "All caught up"}
            </p>
          </div>
        </div>
        <div className={styles.headerActions}>
          {unreadCount > 0 && (
            <div className={styles.unreadPill}>{unreadCount}</div>
          )}
          <button className={styles.readAllBtn} onClick={handleReadAll}>
            <CheckCircle2 size={14} />
            Mark all read
          </button>
        </div>
      </header>

      {/* List */}
      <div className={styles.list}>
        {notifications.length === 0 ? (
          <div className={styles.emptyState}>
            <div className={styles.emptyIconWrap}>
              <Bell size={28} />
            </div>
            <p className={styles.emptyTitle}>No notifications yet</p>
            <p className={styles.emptyDesc}>AI task updates will appear here</p>
          </div>
        ) : (
          notifications.map((item) => (
            <div
              key={item.id}
              className={`${styles.card} ${!item.is_read ? styles.unread : ""} ${styles[`status_${item.status}`]}`}
              onClick={() => handleViewDetail(item.id)}
            >
              {/* Status indicator strip */}
              <div
                className={`${styles.statusStrip} ${styles[`strip_${item.status}`]}`}
              />

              {/* Icon */}
              <div
                className={`${styles.iconWrap} ${styles[`icon_${item.status}`]}`}
              >
                {item.status === "processing" && <Clock size={18} />}
                {item.status === "success" && <CheckCircle2 size={18} />}
                {item.status === "error" && <AlertCircle size={18} />}
              </div>

              {/* Content */}
              <div className={styles.content}>
                <div className={styles.topRow}>
                  <div className={styles.taskMeta}>
                    <span
                      className={`${styles.taskTypeBadge} ${styles[`badge_${item.status}`]}`}
                    >
                      {item.status === "processing" && "Running"}
                      {item.status === "success" && "Complete"}
                      {item.status === "error" && "Failed"}
                    </span>
                    <span className={styles.typePill}>#{item.type}</span>
                    {!item.is_read && <span className={styles.newDot} />}
                  </div>
                  <div className={styles.topRight}>
                    <span className={styles.timestamp}>
                      {formatDate(item.created_at)}
                    </span>
                    <button
                      className={styles.deleteBtn}
                      onClick={(e) => {
                        e.stopPropagation();
                        setSelectedId(item.id);
                        setShowDeleteModal(true);
                      }}
                    >
                      <Trash2 size={32} />
                    </button>
                  </div>
                </div>

                <h3 className={styles.taskName}>{item.task_type}</h3>
                <p className={styles.message}>{item.message}</p>

                {item.status === "error" && (
                  <div className={styles.cardFooter}>
                    <button
                      className={styles.retryBtn}
                      onClick={(e) => handleRetryClick(e, item)}
                    >
                      <RotateCcw size={12} />
                      Retry Task
                    </button>
                  </div>
                )}
              </div>
            </div>
          ))
        )}
      </div>

      {showDeleteModal && (
        <SharePopUpDelete
          isOpen={showDeleteModal}
          onClose={() => {
            setShowDeleteModal(false);
            setSelectedId(null);
          }}
          onConfirm={handleConfirmDelete}
          isLoading={deleteMutation.isPending}
          title="Delete Notification?"
          description={
            <p>
              Are you sure you want to delete this notification? This action
              cannot be undone.
            </p>
          }
        />
      )}

      {showRetryModal && retryTarget && (
        <SharePopUpRetry
          isOpen={showRetryModal}
          onClose={() => {
            setShowRetryModal(false);
            setRetryTarget(null);
          }}
          onConfirm={() => retryMutation.mutate()}
          isLoading={retryMutation.isPending}
          sessionName={retryTarget.displayName}
          {...getRetryWarning(retryTarget.taskType)}
        />
      )}
    </div>
  );
}
