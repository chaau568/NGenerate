"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import SharePopUpDelete from "@/components/SharePopUp_Delete";
import { clientFetch } from "@/lib/client-fetch";
import { useState } from "react";
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

  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [showVideoModal, setShowVideoModal] = useState(false);
  const [selectedVideo, setSelectedVideo] = useState<any | null>(null);

  const { data: currentData } = useQuery({
    queryKey: ["currentTasks"],
    queryFn: fetchCurrentTasks,
    refetchInterval: 5000,
    refetchOnWindowFocus: true,
  });

  const { data: finishedData, isLoading } = useQuery({
    queryKey: ["finishedTasks"],
    queryFn: fetchFinishedTasks,
  });

  const deleteMutation = useMutation({
    mutationFn: async (id: number) => {
      await clientFetch(`/api/project/${id}`, {
        method: "DELETE",
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["currentTasks"] });
      queryClient.invalidateQueries({ queryKey: ["finishedTasks"] });
    },
  });

  // --- จัดการข้อมูลและแก้ปัญหา Redclare Variable ---
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

  const handleWatchVideo = (e: React.MouseEvent, item: any) => {
    e.stopPropagation();
    setSelectedVideo(item);
    setShowVideoModal(true);
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
    } catch (error) {
      console.error(error);
      alert("Download failed.");
    }
  };

  const formatDate = (dateString?: string | null) => {
    if (!dateString) return "-";
    const date = new Date(dateString);
    return date.toLocaleString("th-TH", {
      day: "2-digit",
      month: "short",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  if (isLoading) {
    return <div className={styles.statusText}>Loading Projects...</div>;
  }

  // ================= RENDER EMPTY STATE =================
  if (isEmpty) {
    return (
      <div className={styles.emptyContainer}>
        <div className={styles.emptyContent}>
          <div className={styles.iconWrapper}>
            <FolderOpen size={64} strokeWidth={1.5} />
          </div>
          <h2 className={styles.emptyTitle}>Your Workspace is Empty</h2>
          <p className={styles.emptyDescription}>
            Start your creative journey by creating your first novel session.
            We'll help you turn your story into reality.
          </p>
          <button
            className={styles.createFirstBtn}
            onClick={() => router.push("/library")}
          >
            <PlusCircle size={20} />
            Start Your First Project
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className={styles.container}>
      {/* ================= CURRENT TASKS ================= */}
      {current_tasks.length > 0 && (
        <>
          <h1 className={styles.title}>Current Tasks</h1>
          {current_tasks.map((task) => {
            const isAnalyzing = task.status === "analyzing";
            return (
              <div key={task.session_id} className={styles.currentCard}>
                <div className={styles.currentHeader}>
                  <div className={styles.leftSection}>
                    <h3 className={styles.sessionTitle}>{task.session_name}</h3>
                  </div>
                  <div className={styles.rightGroup}>
                    <span className={styles.progressText}>
                      {task.progress}%{" "}
                      {isAnalyzing && (
                        <span className={styles.working}>{task.status}</span>
                      )}
                    </span>
                    <button
                      className={styles.viewBtn}
                      onClick={() => router.push(`/project/${task.session_id}`)}
                    >
                      <Eye size={16} /> View Detail
                    </button>
                    <button
                      className={styles.deleteBtn}
                      onClick={(e) => {
                        e.stopPropagation();
                        setSelectedId(task.session_id);
                        setShowDeleteModal(true);
                      }}
                    >
                      <Trash2 size={16} />
                    </button>
                  </div>
                </div>
                <div className={styles.progressBarWrapper}>
                  <div
                    className={`${styles.progressBar} ${isAnalyzing ? styles.progressActive : ""}`}
                    style={{
                      width:
                        task.progress === 0 && isAnalyzing
                          ? "15%"
                          : `${task.progress}%`,
                    }}
                  />
                </div>
              </div>
            );
          })}
        </>
      )}

      {/* ================= ANALYSIS HISTORY ================= */}
      {analysis_history.length > 0 && (
        <>
          <h1 className={styles.title}>Analysis History</h1>
          <div className={styles.grid}>
            {analysis_history.map((item) => (
              <div
                key={item.session_id}
                className={styles.expandCard}
                onClick={() => router.push(`/project/${item.session_id}`)}
              >
                <div className={styles.cardContent}>
                  <div className={styles.coverWrapper}>
                    <Image
                      src={getCoverUrl(item.cover)}
                      alt={item.session_name}
                      fill
                      className={styles.coverImg}
                      unoptimized
                    />
                  </div>
                  <div className={styles.infoSection}>
                    <h3 className={styles.cardTitle}>{item.session_name}</h3>
                    <p className={styles.status}>Status: {item.status}</p>
                    <div className={styles.extraInfo}>
                      <p>Create: {formatDate(item.created_at)}</p>
                      <p>Finish: {formatDate(item.analysis_finished_at)}</p>
                    </div>
                  </div>
                </div>
                <div className={styles.actions}>
                  <button
                    className={styles.generateBtn}
                    onClick={(e) => {
                      e.stopPropagation();
                      router.push(
                        `/project/${item.session_id}/summary/generate`,
                      );
                    }}
                  >
                    <Star size={16} /> Generate Video
                  </button>
                  <button
                    className={styles.deleteBtn}
                    onClick={(e) => {
                      e.stopPropagation();
                      setSelectedId(item.session_id);
                      setShowDeleteModal(true);
                    }}
                  >
                    <Trash2 size={16} />
                  </button>
                </div>
              </div>
            ))}
          </div>
        </>
      )}

      {/* ================= GENERATION HISTORY ================= */}
      {generation_history.length > 0 && (
        <>
          <h1 className={styles.title}>Generation History</h1>
          <div className={styles.grid}>
            {generation_history.map((item) => (
              <div
                key={item.session_id}
                className={styles.expandCard}
                onClick={() => router.push(`/project/${item.session_id}`)}
              >
                <div className={styles.cardContent}>
                  <div className={styles.coverWrapper}>
                    <Image
                      src={getCoverUrl(item.cover)}
                      alt={item.session_name}
                      fill
                      className={styles.coverImg}
                      unoptimized
                    />
                  </div>
                  <div className={styles.infoSection}>
                    <h3 className={styles.cardTitle}>{item.session_name}</h3>
                    <p className={styles.version}>Version - {item.version}</p>
                    <div className={styles.extraInfo}>
                      <p>Create: {formatDate(item.created_at)}</p>
                      <p>Finish: {formatDate(item.generation_finished_at)}</p>
                      <p>Storage: {item.file_size} MB</p>
                    </div>
                  </div>
                </div>
                <div className={styles.actions}>
                  <button
                    className={styles.watchBtn}
                    onClick={(e) => handleWatchVideo(e, item)}
                  >
                    <Play size={18} /> Watch The Video
                  </button>
                  <button
                    className={styles.downloadBtn}
                    onClick={(e) =>
                      handleDownload(e, item.session_id, item.video_id)
                    }
                  >
                    <Download size={18} />
                  </button>
                  <button
                    className={styles.deleteBtn}
                    onClick={(e) => {
                      e.stopPropagation();
                      setSelectedId(item.session_id);
                      setShowDeleteModal(true);
                    }}
                  >
                    <Trash2 size={18} />
                  </button>
                </div>
              </div>
            ))}
          </div>
        </>
      )}

      {/* ================= FAILED HISTORY ================= */}
      {failed_history.length > 0 && (
        <>
          <h1 className={styles.title}>Failed History</h1>
          <div className={styles.grid}>
            {failed_history.map((item) => (
              <div
                key={item.session_id}
                className={styles.expandCard}
                style={{ opacity: 0.7 }}
                onClick={() => router.push(`/project/${item.session_id}`)}
              >
                <div className={styles.cardContent}>
                  <div className={styles.coverWrapper}>
                    <Image
                      src={getCoverUrl(item.cover)}
                      alt={item.session_name}
                      fill
                      className={styles.coverImg}
                      unoptimized
                    />
                  </div>
                  <div className={styles.infoSection}>
                    <h3 className={styles.cardTitle}>{item.session_name}</h3>
                    <p className={styles.failedStatus}>Status: Failed</p>
                    <div className={styles.extraInfo}>
                      <p>Create: {formatDate(item.created_at)}</p>
                    </div>
                  </div>
                </div>
                <div className={styles.actions}>
                  <button
                    className={styles.deleteBtn}
                    onClick={(e) => {
                      e.stopPropagation();
                      setSelectedId(item.session_id);
                      setShowDeleteModal(true);
                    }}
                  >
                    <Trash2 size={18} />
                  </button>
                </div>
              </div>
            ))}
          </div>
        </>
      )}

      {/* Modals */}
      {showDeleteModal && (
        <SharePopUpDelete
          isOpen={showDeleteModal}
          onClose={() => {
            setShowDeleteModal(false);
            setSelectedId(null);
          }}
          onConfirm={handleConfirmDelete}
          isLoading={deleteMutation.isPending}
          title="Delete Project?"
          description={
            <p>
              Are you sure you want to delete this project? This action cannot
              be undone.
            </p>
          }
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
