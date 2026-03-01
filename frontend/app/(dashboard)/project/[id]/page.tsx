"use client";

import { useParams, useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { ChevronLeft, CheckCircle2, Clock, AlertCircle } from "lucide-react";
import { fetchProjectDetail } from "@/app/services/project-step";
import styles from "./page.module.css";

export default function ProjectDetailPage() {
  const params = useParams();
  const id = params.id as string;
  const router = useRouter();

  const { data, isLoading } = useQuery({
    queryKey: ["project-detail", id],
    queryFn: () => fetchProjectDetail(id),
    refetchInterval: 5000,
    refetchOnWindowFocus: true,
    enabled: !!id,
  });

  const formatTime = (dateString?: string | null) => {
    if (!dateString) return "-";
    const date = new Date(dateString);
    return date.toLocaleTimeString([], {
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  if (isLoading || !data) return <p>Loading...</p>;

  let overallStatus: "success" | "processing" | "failed" = "processing";

  if (data.steps.some((s) => s.status === "failed")) {
    overallStatus = "failed";
  } else if (data.steps.every((s) => s.status === "success")) {
    overallStatus = "success";
  } else if (data.steps.some((s) => s.status === "processing")) {
    overallStatus = "processing";
  }

  return (
    <div className={styles.container}>
      <header className={styles.header}>
        <div className={styles.headerLeft}>
          <button onClick={() => router.back()} className={styles.backBtn}>
            <ChevronLeft size={22} />
          </button>
          <div>
            <h1 className={styles.title}>{data.session_name}</h1>
            <p className={styles.subtitle}>
              Started: {new Date(data.started_at).toLocaleString()}
            </p>
          </div>
        </div>
      </header>

      <div className={`${styles.progressSection} ${styles[overallStatus]}`}>
        <h2>OVERALL PROGRESS</h2>
        <div className={styles.progressText}>
          {data.overall_progress}% IN PROGRESS
        </div>
        <div className={styles.progressBar}>
          <div
            className={styles.progressFill}
            style={{ width: `${data.overall_progress}%` }}
          />
        </div>
      </div>

      <div className={styles.workflow}>
        <h2>Project Workflow</h2>

        {data.steps.map((step) => {
          const isSuccess = step.status === "success";
          const isProcessing = step.status === "processing";
          const isFail = step.status === "failed";

          return (
            <div
              key={step.id}
              className={`${styles.step} ${styles[step.status]}`}
            >
              <div className={styles.stepLeft}>
                <div className={styles.iconWrapper}>
                  {isSuccess && <CheckCircle2 size={26} />}
                  {isProcessing && <Clock size={26} className={styles.spin} />}
                  {isFail && <AlertCircle size={26} />}
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
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
