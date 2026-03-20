"use client";

import { useParams, useRouter } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  ChevronLeft,
  CheckCircle2,
  Clock,
  RotateCcw,
  AlertCircle,
} from "lucide-react";
import { fetchNotificationDetail } from "@/app/services/notification-detail";
import SharePopUpRetry from "@/components/SharePopUp_Retry";
import { clientFetch } from "@/lib/client-fetch";
import { useState } from "react";
import styles from "./page.module.css";

export default function NotificationDetailPage() {
  const params = useParams();
  const id = params.id as string;
  const router = useRouter();
  const queryClient = useQueryClient();

  const [showRetryModal, setShowRetryModal] = useState(false);

  const { data, isLoading } = useQuery({
    queryKey: ["notification-detail", id],
    queryFn: () => fetchNotificationDetail(id),
    refetchInterval: 5000,
    refetchOnWindowFocus: true,
    enabled: !!id,
  });

  const retryMutation = useMutation({
    mutationFn: async () => {
      if (!data) return;
      if (data.task_type === "upload") {
        await clientFetch(`/api/notification/${id}/retry-upload`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ novel_id: data.novel_id }),
        });
      } else {
        await clientFetch(`/api/sessions/retry/${data.session_id}/`, {
          method: "POST",
        });
      }
    },
    onSuccess: () => {
      setShowRetryModal(false);
      queryClient.invalidateQueries({ queryKey: ["notification-detail", id] });
      queryClient.invalidateQueries({ queryKey: ["notifications"] });
    },
  });

  const formatTime = (dateString?: string | null) => {
    if (!dateString) return "—";
    return new Date(dateString).toLocaleTimeString([], {
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  if (isLoading || !data) {
    return (
      <div className={styles.loadingState}>
        <div className={styles.loadingBar}>
          <div className={styles.loadingFill} />
        </div>
        <span>Loading Notification Detail…</span>
      </div>
    );
  }

  const processing = data.processing;
  const taskType = data.task_type;
  const progressLabel = taskType === "generation" ? "Generating" : "Analyzing";

  const overallStatus: "success" | "processing" | "failed" =
    data.status === "success"
      ? "success"
      : data.status === "error"
        ? "failed"
        : "processing";

  const retryDisplayName =
    data.session_name || data.novel_info?.title || data.task_name || taskType;

  const getRetryWarning = () => {
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

  return (
    <div className={styles.container}>
      {/* Header */}
      <header className={styles.header}>
        <button onClick={() => router.back()} className={styles.backBtn}>
          <ChevronLeft size={20} />
        </button>
        <div className={styles.headerInfo}>
          <div className={styles.headerTop}>
            <span
              className={`${styles.statusChip} ${styles[`chip_${overallStatus}`]}`}
            >
              {overallStatus === "success" && <CheckCircle2 size={12} />}
              {overallStatus === "processing" && (
                <Clock size={12} className={styles.spin} />
              )}
              {overallStatus === "failed" && <AlertCircle size={12} />}
              {overallStatus.charAt(0).toUpperCase() + overallStatus.slice(1)}
            </span>
          </div>
          <h1 className={styles.title}>{data.task_name}</h1>
          <p className={styles.subtitle}>{data.message}</p>
        </div>
      </header>

      {processing ? (
        <>
          {/* Progress Card */}
          <div
            className={`${styles.progressCard} ${styles[`progress_${overallStatus}`]}`}
          >
            <div className={styles.progressHeader}>
              <span className={styles.progressLabel}>Overall Progress</span>
              <span className={styles.progressValue}>
                {processing.overall_progress}%
              </span>
            </div>
            <div className={styles.progressTrack}>
              <div
                className={`${styles.progressFill} ${styles[`fill_${overallStatus}`]}`}
                style={{ width: `${processing.overall_progress}%` }}
              />
            </div>
            <p className={styles.progressSublabel}>
              {overallStatus === "processing" &&
                `${progressLabel} in progress…`}
              {overallStatus === "success" && "Task completed successfully"}
              {overallStatus === "failed" && "Task encountered an error"}
            </p>
          </div>

          {/* Workflow Steps */}
          <section className={styles.workflowSection}>
            <h2 className={styles.sectionTitle}>
              <span className={styles.sectionDot} />
              AI Workflow
            </h2>
            <div className={styles.stepList}>
              {processing.steps?.map((step: any, index: number) => {
                const isSuccess =
                  step.status === "analyzed" ||
                  step.status === "generated" ||
                  step.status === "success";
                const isProcessing =
                  step.status === "analyzing" ||
                  step.status === "generating" ||
                  step.status === "processing";
                const isFail =
                  step.status === "fail" || step.status === "failed";
                const isPending = step.status === "pending";

                const stepState = isSuccess
                  ? "success"
                  : isProcessing
                    ? "processing"
                    : isFail
                      ? "error"
                      : "pending";

                return (
                  <div
                    key={step.id}
                    className={`${styles.step} ${styles[`step_${stepState}`]}`}
                  >
                    {/* Step number connector */}
                    <div className={styles.stepConnector}>
                      <div
                        className={`${styles.stepDot} ${styles[`dot_${stepState}`]}`}
                      >
                        {isSuccess && <CheckCircle2 size={14} />}
                        {isProcessing && (
                          <Clock size={14} className={styles.spin} />
                        )}
                        {isFail && <AlertCircle size={14} />}
                        {isPending && (
                          <span className={styles.stepNum}>{index + 1}</span>
                        )}
                      </div>
                      {index < (processing.steps?.length ?? 0) - 1 && (
                        <div
                          className={`${styles.stepLine} ${styles[`line_${stepState}`]}`}
                        />
                      )}
                    </div>

                    {/* Step content */}
                    <div className={styles.stepContent}>
                      <div className={styles.stepHeader}>
                        <strong className={styles.stepName}>{step.name}</strong>
                        <span
                          className={`${styles.stepBadge} ${styles[`badge_${stepState}`]}`}
                        >
                          {step.status.toUpperCase()}
                        </span>
                      </div>
                      <div className={styles.stepTime}>
                        <Clock size={11} />
                        Started {formatTime(step.started_at)}
                        {step.finished_at && (
                          <> &middot; Done {formatTime(step.finished_at)}</>
                        )}
                      </div>
                      {step.error_message && (
                        <div className={styles.errorBox}>
                          <AlertCircle size={12} />
                          <span>{step.error_message}</span>
                        </div>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          </section>

          {overallStatus === "failed" && (
            <button
              className={styles.retryLargeBtn}
              onClick={() => setShowRetryModal(true)}
            >
              <RotateCcw size={16} />
              Retry Task
            </button>
          )}
        </>
      ) : (
        /* Simple status card (no workflow) */
        <div
          className={`${styles.simpleCard} ${styles[`simpleCard_${overallStatus}`]}`}
        >
          <div className={styles.simpleHeader}>
            <div
              className={`${styles.simpleIcon} ${styles[`simpleIcon_${overallStatus}`]}`}
            >
              {overallStatus === "failed" && <AlertCircle size={24} />}
              {overallStatus === "success" && <CheckCircle2 size={24} />}
              {overallStatus === "processing" && (
                <Clock size={24} className={styles.spin} />
              )}
            </div>
            <div>
              <div className={styles.simpleStatusLabel}>Task Status</div>
              <div
                className={`${styles.simpleStatusValue} ${styles[`statusText_${overallStatus}`]}`}
              >
                {overallStatus.toUpperCase()}
              </div>
            </div>
          </div>

          {data.novel_info && (
            <div className={styles.infoGrid}>
              <div className={styles.infoItem}>
                <span className={styles.infoLabel}>Novel Title</span>
                <strong className={styles.infoValue}>
                  {data.novel_info.title}
                </strong>
              </div>
              <div className={styles.infoItem}>
                <span className={styles.infoLabel}>Created</span>
                <strong className={styles.infoValue}>
                  {new Date(data.created_at).toLocaleString()}
                </strong>
              </div>
            </div>
          )}

          {overallStatus === "failed" && (
            <button
              className={styles.retryLargeBtn}
              onClick={() => setShowRetryModal(true)}
            >
              <RotateCcw size={16} />
              Retry Task
            </button>
          )}
        </div>
      )}

      {showRetryModal && (
        <SharePopUpRetry
          isOpen={showRetryModal}
          onClose={() => setShowRetryModal(false)}
          onConfirm={() => retryMutation.mutate()}
          isLoading={retryMutation.isPending}
          sessionName={retryDisplayName}
          {...getRetryWarning()}
        />
      )}
    </div>
  );
}
