"use client";

import { useEffect, useState, use, useRef } from "react";
import { useRouter } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { fetchNotifications } from "@/app/services/notification";
import SharePopUpDelete from "@/components/SharePopUp_Delete";
import { clientFetch } from "@/lib/client-fetch";
import {
  Bell,
  CheckCircle2,
  Clock,
  Trash2,
  RotateCcw,
  AlertCircle,
} from "lucide-react";
import styles from "./page.module.css";

export default function NotificationPage() {
  const router = useRouter();
  const queryClient = useQueryClient();

  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [selectedId, setSelectedId] = useState<number | null>(null);

  // =========================
  // FETCH (ใช้ service)
  // =========================
  const { data: notifications = [], isLoading } = useQuery({
    queryKey: ["notifications"],
    queryFn: fetchNotifications,
    refetchInterval: 5000,
    refetchOnWindowFocus: true,
    refetchIntervalInBackground: false,
  });

  // =========================
  // MARK READ
  // =========================
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

  // =========================
  // DELETE
  // =========================
  const deleteMutation = useMutation({
    mutationFn: async (id: number) => {
      await clientFetch(`/api/notification/${id}`, {
        method: "DELETE",
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["notifications"] });
    },
  });

  const isDeleting = deleteMutation.isPending;

  const handleReadAll = async () => {
    const unread = notifications.filter((n) => !n.is_read);
    await Promise.all(unread.map((n) => markReadMutation.mutateAsync(n.id)));
  };

  const handleViewDetail = (id: number) => {
    router.push(`/notification/${id}`);
  };

  const handleRetry = (e: React.MouseEvent, id: number) => {
    e.stopPropagation();
    alert(`Retrying task for notification ID: ${id}`);
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

  const handleConfirmDelete = () => {
    if (!selectedId) return;

    deleteMutation.mutate(selectedId, {
      onSuccess: () => {
        setShowDeleteModal(false);
        setSelectedId(null);
      },
    });
  };

  if (isLoading) {
    return <div className={styles.statusText}>Loading Notifications...</div>;
  }

  return (
    <div className={styles.container}>
      <header className={styles.header}>
        <h1>Notifications</h1>

        <div className={styles.rightGroup}>
          <span className={styles.badge}>
            {notifications.filter((n) => !n.is_read).length} Unread
          </span>

          <button className={styles.readAllBtn} onClick={handleReadAll}>
            <CheckCircle2 size={18} /> Read All
          </button>
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
              onClick={() => handleViewDetail(item.id)}
            >
              <div className={styles.iconWrapper}>
                {item.status === "processing" && (
                  <Clock className={styles.statusIconProcessing} size={24} />
                )}
                {item.status === "success" && (
                  <CheckCircle2
                    className={styles.statusIconSuccess}
                    size={24}
                  />
                )}
                {item.status === "error" && (
                  <AlertCircle className={styles.statusIconError} size={24} />
                )}
              </div>

              <div className={styles.content}>
                <div className={styles.contentHeader}>
                  <div className={styles.taskInfo}>
                    <h3 className={styles.taskName}>{item.task_name}</h3>
                    <span className={styles.time}>
                      {formatDate(item.created_at)}
                    </span>
                  </div>

                  <div className={styles.topActions}>
                    <button
                      className={styles.deleteBtn}
                      onClick={(e) => {
                        e.stopPropagation();
                        setSelectedId(item.id);
                        setShowDeleteModal(true);
                      }}
                    >
                      <Trash2 size={18} />
                    </button>
                  </div>
                </div>

                <p className={styles.message}>{item.message}</p>

                <div className={styles.footer}>
                  <div className={styles.tags}>
                    <span className={styles.typeTag}>#{item.type}</span>
                    {!item.is_read && (
                      <span className={styles.newBadge}>New</span>
                    )}
                  </div>

                  <div className={styles.actions}>
                    {item.status === "error" && (
                      <button
                        className={styles.retryBtn}
                        onClick={(e) => handleRetry(e, item.id)}
                      >
                        <RotateCcw size={14} /> Retry
                      </button>
                    )}
                  </div>
                </div>
              </div>
            </div>
          ))
        )}

        {showDeleteModal && (
          <SharePopUpDelete
            isOpen={showDeleteModal}
            onClose={() => {
              setShowDeleteModal(false);
              setSelectedId(null);
            }}
            onConfirm={handleConfirmDelete}
            isLoading={isDeleting}
            title="Delete Notification?"
            description={
              <p>
                Are you sure you want to delete this notification? This action
                cannot be undone.
              </p>
            }
          />
        )}
      </div>
    </div>
  );
}
