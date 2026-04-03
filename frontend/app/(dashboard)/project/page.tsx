"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import SharePopUpDelete from "@/components/SharePopUp_Delete";
import SharePopUpRetry from "@/components/SharePopUp_Retry";
import { clientFetch } from "@/lib/client-fetch";
import { useState, useEffect, useRef } from "react";
import { useQuery } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { fetchCurrentTasks, fetchFinishedTasks } from "@/app/services/project";
import styles from "./page.module.css";
import Image from "next/image";
import {
  Eye,
  Trash2,
  Play,
  Star,
  Download,
  FolderOpen,
  PlusCircle,
  RotateCcw,
  ChevronRight,
} from "lucide-react";
import SharePopUpVideo from "@/components/SharePopUp_Video";

const getCoverUrl = (cover: string | null) => {
  if (!cover) return "/default-cover.jpg";
  if (cover.startsWith("http")) return cover;
  return `${process.env.NEXT_PUBLIC_API_BASE_URL}${cover}`;
};

export default function ProjectPage() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const prevCurrentCount = useRef(0);

  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [showVideoModal, setShowVideoModal] = useState(false);
  const [selectedVideo, setSelectedVideo] = useState<any | null>(null);

  const [showRetryModal, setShowRetryModal] = useState(false);
  const [retryTarget, setRetryTarget] = useState<{
    sessionId: number;
    sessionName: string;
  } | null>(null);

  const [deleteTarget, setDeleteTarget] = useState<{
    type: "session" | "run";
    sessionId: number;
    runId?: number;
  } | null>(null);

  const { data: currentData } = useQuery({
    queryKey: ["currentTasks"],
    queryFn: fetchCurrentTasks,
    refetchInterval: 5000,
    refetchOnWindowFocus: true,
  });

  const { data: finishedData, isLoading } = useQuery({
    queryKey: ["finishedTasks"],
    queryFn: fetchFinishedTasks,
    refetchOnWindowFocus: true,
  });

  useEffect(() => {
    const currentCount = currentData?.current_tasks?.length ?? 0;
    if (
      prevCurrentCount.current > 0 &&
      currentCount < prevCurrentCount.current
    ) {
      queryClient.invalidateQueries({ queryKey: ["finishedTasks"] });
    }
    prevCurrentCount.current = currentCount;
  }, [currentData, queryClient]);

  const current_tasks = currentData?.current_tasks ?? [];
  const analysis_history = finishedData?.analysis_history ?? [];
  const generation_history = finishedData?.generation_history ?? [];
  const failed_history = finishedData?.failed_history ?? [];

  const isEmpty =
    !isLoading &&
    current_tasks.length === 0 &&
    analysis_history.length === 0 &&
    generation_history.length === 0 &&
    failed_history.length === 0;

  const deleteSessionMutation = useMutation({
    mutationFn: async (sessionId: number) => {
      await clientFetch(`/api/project/${sessionId}`, { method: "DELETE" });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["currentTasks"] });
      queryClient.invalidateQueries({ queryKey: ["finishedTasks"] });
      setShowDeleteModal(false);
      setDeleteTarget(null);
    },
  });

  const deleteRunMutation = useMutation({
    mutationFn: async (runId: number) => {
      await clientFetch(`/api/sessions/generation-run/${runId}`, {
        method: "DELETE",
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["finishedTasks"] });
      setShowDeleteModal(false);
      setDeleteTarget(null);
    },
  });

  const retryMutation = useMutation({
    mutationFn: async (sessionId: number) => {
      await clientFetch(`/api/sessions/retry/${sessionId}/`, {
        method: "POST",
      });
    },
    onSuccess: () => {
      setShowRetryModal(false);
      setRetryTarget(null);
      queryClient.invalidateQueries({ queryKey: ["currentTasks"] });
      queryClient.invalidateQueries({ queryKey: ["finishedTasks"] });
    },
  });

  const handleConfirmDelete = () => {
    if (!deleteTarget) return;

    if (deleteTarget.type === "run" && deleteTarget.runId) {
      deleteRunMutation.mutate(deleteTarget.runId);
    } else {
      deleteSessionMutation.mutate(deleteTarget.sessionId);
    }
  };

  const handleConfirmRetry = () => {
    if (!retryTarget) return;
    retryMutation.mutate(retryTarget.sessionId);
  };

  const handleDownload = async (
    e: React.MouseEvent,
    sessionId: number,
    videoId: number,
  ) => {
    e.stopPropagation();
    try {
      const res = await clientFetch(
        `/api/project/${sessionId}?download=${videoId}`,
        { method: "GET" },
      );
      if (!res.ok) throw new Error("Download failed");
      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `video-${videoId}.mp4`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
    } catch {
      alert("Download failed.");
    }
  };

  const formatDate = (dateString?: string | null) => {
    if (!dateString) return "-";
    return new Date(dateString).toLocaleString("th-TH", {
      day: "2-digit",
      month: "short",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  if (isLoading)
    return (
      <div className={styles.loadingState}>
        <div className={styles.loadingBar}>
          <div className={styles.loadingFill} />
        </div>
        <span>Loading Projects…</span>
      </div>
    );

  if (isEmpty) {
    return (
      <div className={styles.emptyContainer}>
        <div className={styles.emptyContent}>
          <div className={styles.emptyIcon}>
            <FolderOpen size={52} strokeWidth={1.2} />
          </div>
          <h2 className={styles.emptyTitle}>Workspace is Empty</h2>
          <p className={styles.emptyDesc}>
            Turn your story into a video. Start your first session.
          </p>
          <button
            className={styles.emptyBtn}
            onClick={() => router.push("/library")}
          >
            <PlusCircle size={16} /> Start First Project
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className={styles.container}>
      {/* ── CURRENT TASKS ── */}
      {current_tasks.length > 0 && (
        <section className={styles.section}>
          <div className={styles.sectionHead}>
            <span className={styles.sectionLabel}>Live</span>
            <h2 className={styles.sectionTitle}>Running</h2>
          </div>
          <div className={styles.runningList}>
            {current_tasks.map((task: any) => {
              const isGen = task.status === "generating";
              return (
                <div
                  key={task.session_id}
                  className={styles.runningCard}
                >
                  <div className={styles.runningTop}>
                    <div className={styles.runningLeft}>
                      <span
                        className={`${styles.liveChip} ${isGen ? styles.liveChipGen : ""}`}
                      >
                        <span className={styles.liveDot} />
                        {isGen ? "Generating" : "Analyzing"}
                      </span>
                      <p className={styles.runningName}>{task.session_name}</p>
                    </div>
                    <div className={styles.runningRight}>
                      <span className={styles.runningPct}>
                        {task.progress}%
                      </span>
                      <button
                        className={styles.iconBtnDanger}
                        onClick={(e) => {
                          e.stopPropagation();
                          setDeleteTarget({
                            type: "session",
                            sessionId: task.session_id,
                          });
                          setShowDeleteModal(true);
                        }}
                      >
                        <Trash2 size={15} />
                      </button>
                    </div>
                  </div>
                  <div className={styles.runningBar}>
                    <div
                      className={`${styles.runningFill} ${isGen ? styles.fillGen : styles.fillAnalyze}`}
                      style={{
                        width: task.progress === 0 ? "4%" : `${task.progress}%`,
                      }}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        </section>
      )}

      {/* ── THREE COLUMNS ── */}
      <div className={styles.columns}>
        {/* ANALYZED */}
        {analysis_history.length > 0 && (
          <div className={styles.col}>
            <div className={styles.colHead}>
              <span
                className={styles.colDot}
                style={{ background: "#22c55e" }}
              />
              <span className={styles.colTitle}>Analyzed</span>
              <span className={styles.colCount}>{analysis_history.length}</span>
            </div>
            <div className={styles.cardStack}>
              {analysis_history.map((item: any) => (
                <div
                  key={item.session_id}
                  className={styles.card}
                  onClick={() => router.push(`/project/${item.session_id}`)}
                >
                  <div className={styles.cardCover}>
                    <Image
                      src={getCoverUrl(item.cover)}
                      alt=""
                      fill
                      className={styles.coverImg}
                      unoptimized
                    />
                    <div className={styles.coverOverlay} />
                    <span
                      className={styles.cardStatusChip}
                      style={{
                        background: "rgba(34,197,94,0.2)",
                        color: "#86efac",
                        borderColor: "rgba(34,197,94,0.35)",
                      }}
                    >
                      Analyzed
                    </span>
                  </div>
                  <div className={styles.cardBody}>
                    <p className={styles.cardName}>{item.session_name}</p>
                    <p className={styles.cardDate}>
                      {formatDate(item.analysis_finished_at)}
                    </p>
                  </div>
                  <div className={styles.cardFooter}>
                    <button
                      className={styles.primaryBtn}
                      onClick={(e) => {
                        e.stopPropagation();
                        router.push(
                          `/project/${item.session_id}/summary/generate`,
                        );
                      }}
                    >
                      <Star size={13} /> Generate
                    </button>
                    <button
                      className={styles.ghostBtn}
                      onClick={(e) => {
                        e.stopPropagation();
                        router.push(`/project/${item.session_id}`);
                      }}
                    >
                      <Eye size={13} />
                    </button>
                    <button
                      className={styles.dangerBtn}
                      onClick={(e) => {
                        e.stopPropagation();
                        setDeleteTarget({
                          type: "session",
                          sessionId: item.session_id,
                        });
                        setShowDeleteModal(true);
                      }}
                    >
                      <Trash2 size={13} />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* GENERATED */}
        {generation_history.length > 0 && (
          <div className={styles.col}>
            <div className={styles.colHead}>
              <span
                className={styles.colDot}
                style={{ background: "#3b82f6" }}
              />
              <span className={styles.colTitle}>Generated</span>
              <span className={styles.colCount}>
                {generation_history.length}
              </span>
            </div>
            <div className={styles.cardStack}>
              {generation_history.map((item: any) => (
                <div
                  key={item.session_id}
                  className={styles.card}
                  onClick={() => router.push(`/project/${item.session_id}`)}
                >
                  <div className={styles.cardCover}>
                    <Image
                      src={getCoverUrl(item.cover)}
                      alt=""
                      fill
                      className={styles.coverImg}
                      unoptimized
                    />
                    <div className={styles.coverOverlay} />
                    <span
                      className={styles.cardStatusChip}
                      style={{
                        background: "rgba(59,130,246,0.2)",
                        color: "#93c5fd",
                        borderColor: "rgba(59,130,246,0.35)",
                      }}
                    >
                      v{item.version}
                    </span>
                    {/* Play overlay */}
                    <button
                      className={styles.playOverlay}
                      onClick={(e) => {
                        e.stopPropagation();
                        setSelectedVideo(item);
                        setShowVideoModal(true);
                      }}
                    >
                      <Play size={22} fill="white" />
                    </button>
                  </div>
                  <div className={styles.cardBody}>
                    <p className={styles.cardName}>{item.session_name}</p>
                    <p className={styles.cardDate}>
                      {formatDate(item.generation_finished_at)}
                    </p>
                    <p className={styles.cardMeta}>{item.file_size} MB</p>
                  </div>
                  <div className={styles.cardFooter}>
                    <button
                      className={styles.primaryBtn}
                      style={{
                        background: "rgba(59,130,246,0.15)",
                        borderColor: "rgba(59,130,246,0.35)",
                        color: "#93c5fd",
                      }}
                      onClick={(e) => {
                        e.stopPropagation();
                        setSelectedVideo(item);
                        setShowVideoModal(true);
                      }}
                    >
                      <Play size={13} /> Watch
                    </button>
                    <button
                      className={styles.ghostBtn}
                      onClick={(e) =>
                        handleDownload(e, item.session_id, item.video_id)
                      }
                    >
                      <Download size={13} />
                    </button>
                    <button
                      className={styles.dangerBtn}
                      onClick={(e) => {
                        e.stopPropagation();
                        setDeleteTarget({
                          type: "run",
                          sessionId: item.session_id,
                          runId: item.generation_run_id,
                        });
                        setShowDeleteModal(true);
                      }}
                    >
                      <Trash2 size={13} />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* FAILED */}
        {failed_history.length > 0 && (
          <div className={styles.col}>
            <div className={styles.colHead}>
              <span
                className={styles.colDot}
                style={{ background: "#ef4444" }}
              />
              <span className={styles.colTitle}>Failed</span>
              <span className={styles.colCount}>{failed_history.length}</span>
            </div>
            <div className={styles.cardStack}>
              {failed_history.map((item: any) => (
                <div
                  key={item.session_id}
                  className={`${styles.card} ${styles.cardFailed}`}
                  onClick={() => router.push(`/project/${item.session_id}`)}
                >
                  <div className={styles.cardCover}>
                    <Image
                      src={getCoverUrl(item.cover)}
                      alt=""
                      fill
                      className={styles.coverImg}
                      unoptimized
                    />
                    <div
                      className={`${styles.coverOverlay} ${styles.coverOverlayFailed}`}
                    />
                    <span
                      className={styles.cardStatusChip}
                      style={{
                        background: "rgba(239,68,68,0.2)",
                        color: "#fca5a5",
                        borderColor: "rgba(239,68,68,0.35)",
                      }}
                    >
                      Failed
                    </span>
                  </div>
                  <div className={styles.cardBody}>
                    <p className={styles.cardName}>{item.session_name}</p>
                    <p className={styles.cardDate}>
                      {formatDate(item.created_at)}
                    </p>
                  </div>
                  <div className={styles.cardFooter}>
                    <button
                      className={styles.retryBtn}
                      onClick={(e) => {
                        e.stopPropagation();
                        setRetryTarget({
                          sessionId: item.session_id,
                          sessionName: item.session_name,
                        });
                        setShowRetryModal(true);
                      }}
                    >
                      <RotateCcw size={13} /> Retry
                    </button>
                    <button
                      className={styles.ghostBtn}
                      onClick={(e) => {
                        e.stopPropagation();
                        router.push(`/project/${item.session_id}`);
                      }}
                    >
                      <Eye size={13} />
                    </button>
                    <button
                      className={styles.dangerBtn}
                      onClick={(e) => {
                        e.stopPropagation();

                        if (
                          item.failed_type === "generation" &&
                          item.generation_run_id
                        ) {
                          setDeleteTarget({
                            type: "run",
                            sessionId: item.session_id,
                            runId: item.generation_run_id,
                          });
                        } else {
                          setDeleteTarget({
                            type: "session",
                            sessionId: item.session_id,
                          });
                        }
                        setShowDeleteModal(true);
                      }}
                    >
                      <Trash2 size={13} />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Modals */}
      {showDeleteModal && (
        <SharePopUpDelete
          isOpen={showDeleteModal}
          onClose={() => {
            setShowDeleteModal(false);
            setDeleteTarget(null);
          }}
          onConfirm={handleConfirmDelete}
          isLoading={
            deleteSessionMutation.isPending || deleteRunMutation.isPending
          }
          title={
            deleteTarget?.type === "run"
              ? "Delete Generation Run?"
              : "Delete Project?"
          }
          description={
            deleteTarget?.type === "run" ? (
              <p>ลบ generation run นี้ออก session และ analysis ยังคงอยู่</p>
            ) : (
              <p>ลบ project ทั้งหมด รวม analysis และ generation ทั้งหมด</p>
            )
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
          onConfirm={handleConfirmRetry}
          isLoading={retryMutation.isPending}
          sessionName={retryTarget.sessionName}
          warningHighlight="การ Retry ไม่ใช่การทำต่อจากการดำเนินงานล่าสุด แต่เป็นการลบการวิเคราะห์เดิมทิ้ง แล้ว สร้างใหม่"
        />
      )}

      <SharePopUpVideo
        isOpen={showVideoModal}
        onClose={() => {
          setShowVideoModal(false);
          setSelectedVideo(null);
        }}
        videoData={selectedVideo}
      />
    </div>
  );
}
