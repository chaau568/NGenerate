"use client";

import { useParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { ChevronLeft } from "lucide-react";
import { fetchNotificationDetail } from "@/app/services/notification-detail";
import { CheckCircle2, Clock, RotateCcw, AlertCircle } from "lucide-react";
import styles from "./page.module.css";

export default function NotificationDetailPage() {
  const params = useParams();
  const id = params.id as string;
  const router = useRouter();

  const { data, isLoading } = useQuery({
    queryKey: ["notification-detail", id],
    queryFn: () => fetchNotificationDetail(id),
    refetchInterval: 5000,
    refetchOnWindowFocus: true,
    enabled: !!id,
  });

  const formatTime = (dateString?: string | null) => {
    if (!dateString) return "-";
    const date = new Date(dateString);
    return date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  };

  if (isLoading || !data) return <p>Loading...</p>;

  const processing = data.processing;

  const overallStatus: "success" | "processing" | "failed" =
    data.status === "success"
      ? "success"
      : data.status === "error"
        ? "failed"
        : "processing";

  return (
    <div className={styles.container}>
      <header className={styles.header}>
        <div className={styles.headerLeft}>
          <button onClick={() => router.back()} className={styles.backBtn}>
            <ChevronLeft size={22} />
          </button>
          <div>
            <h1 className={styles.title}>{data.task_name}</h1>
            <p className={styles.subtitle}>{data.message}</p>
          </div>
        </div>
      </header>

      {processing ? (
        <>
          <div className={`${styles.progressSection} ${styles[overallStatus]}`}>
            <h2>OVERALL PROGRESS</h2>
            <div className={styles.progressText}>
              {processing.overall_progress}% ANALYZING
            </div>
            <div className={styles.progressBar}>
              <div
                className={styles.progressFill}
                style={{ width: `${processing.overall_progress}%` }}
              />
            </div>
          </div>

          <div className={styles.workflow}>
            <h2>AI Workflow</h2>

            {processing.steps?.map((step) => {
              const isSuccess =
                step.status === "analyzed" || step.status === "generated";

              const isProcessing =
                step.status === "analyzing" || step.status === "generating";

              const isFail = step.status === "fail";

              const isPending = step.status === "pending";

              return (
                <div
                  key={step.id}
                  className={`${styles.step} ${styles[step.status] || ""}`}
                >
                  <div className={styles.stepLeft}>
                    <div className={styles.iconWrapper}>
                      {isSuccess && <CheckCircle2 size={26} />}
                      {isProcessing && (
                        <Clock size={26} className={styles.spin} />
                      )}
                      {isFail && <AlertCircle size={26} />}
                      {isPending && <Clock size={26} />}
                    </div>

                    <div>
                      <strong>{step.name}</strong>

                      <div className={styles.timeRow}>
                        <Clock size={14} />
                        Started {formatTime(step.started_at)}
                        {step.finished_at && (
                          <> • Done {formatTime(step.finished_at)}</>
                        )}
                      </div>

                      {step.error_message && (
                        <div className={styles.errorBox}>
                          <AlertCircle size={14} />
                          <span>{step.error_message}</span>
                        </div>
                      )}
                    </div>
                  </div>

                  <div className={styles.stepRight}>
                    <span className={styles.status}>
                      {step.status.toUpperCase()}
                    </span>

                    {isFail && (
                      <button
                        className={styles.retryBtn}
                        onClick={(e) => {
                          e.stopPropagation();
                        }}
                      >
                        <RotateCcw size={16} />
                        Retry
                      </button>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </>
      ) : (
        <div className={`${styles.simpleStatusCard} ${styles[overallStatus]}`}>
          <div className={styles.simpleStatusHeader}>
            {overallStatus === "failed" && <AlertCircle size={40} />}
            {overallStatus === "success" && <CheckCircle2 size={40} />}
            {overallStatus === "processing" && (
              <Clock size={40} className={styles.spin} />
            )}
            <div>
              <div className={styles.statusLabel}>TASK STATUS</div>
              <div className={styles.statusValue}>
                {overallStatus.toUpperCase()}
              </div>
            </div>
          </div>

          {data.novel_info && (
            <div className={styles.infoGrid}>
              <div className={styles.infoItem}>
                <span>Novel Title</span>
                <strong>{data.novel_info.title}</strong>
              </div>
              <div className={styles.infoItem}>
                <span>Created At</span>
                <strong>{new Date(data.created_at).toLocaleString()}</strong>
              </div>
            </div>
          )}

          {overallStatus === "failed" && (
            <button
              className={styles.retryLargeBtn}
              onClick={() => alert("Retrying...")}
            >
              <RotateCcw size={20} /> Retry Task
            </button>
          )}
        </div>
      )}
    </div>
  );
}
