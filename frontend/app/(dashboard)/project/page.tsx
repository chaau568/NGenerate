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
import { Eye, Trash2, Play, Star, Download } from "lucide-react";
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

  const handleWatchVideo = (e: React.MouseEvent, item: any) => {
    e.stopPropagation();
    setSelectedVideo(item);
    setShowVideoModal(true);
  };

  const isDeleting = deleteMutation.isPending;

  if (isLoading || !finishedData) {
    return <div className={styles.statusText}>Loading Projects...</div>;
  }

  const current_tasks = currentData?.current_tasks ?? [];
  const { analysis_history, generation_history } = finishedData;

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
      const res = await fetch(`/api/project/${sessionId}?download=${videoId}`, {
        method: "GET",
      });

      if (!res.ok) {
        throw new Error("Download failed");
      }

      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);

      const a = document.createElement("a");
      a.href = url;

      const contentDisposition = res.headers.get("Content-Disposition");
      let filename = `video-${videoId}.mp4`;

      if (contentDisposition) {
        const utf8Match = contentDisposition.match(/filename\*=UTF-8''(.+)/);
        if (utf8Match?.[1]) {
          filename = decodeURIComponent(utf8Match[1]);
        } else {
          const match = contentDisposition.match(/filename="?([^"]+)"?/);
          if (match?.[1]) filename = match[1];
        }
      }

      a.download = filename;
      document.body.appendChild(a);
      a.click();
      a.remove();

      window.URL.revokeObjectURL(url);
    } catch (error) {
      console.error(error);
      alert("Download failed.");
    }
  };

  const formatDateTime = (dateString?: string | null) => {
    if (!dateString) return "-";
    const date = new Date(dateString);
    return date.toLocaleString("th-TH", {
      timeZone: "Asia/Bangkok",
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
    });
  };

  return (
    <div className={styles.container}>
      {/* ================= CURRENT TASKS ================= */}
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
                className={`${styles.progressBar} ${
                  isAnalyzing ? styles.progressActive : ""
                }`}
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

      {/* ================= ANALYSIS HISTORY ================= */}
      <h1 className={styles.title}>Analysis History</h1>

      <div className={styles.grid}>
        {analysis_history.map((item) => (
          <div
            key={item.session_id}
            className={styles.expandCard}
            style={{ cursor: "pointer" }}
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
                  <p>Create: {formatDateTime(item.created_at)}</p>
                  <p>Finish: {formatDateTime(item.analysis_finished_at)}</p>
                </div>
              </div>
            </div>

            <div className={styles.actions}>
              <button
                className={styles.generateBtn}
                onClick={(e) => {
                  e.stopPropagation();
                  router.push(`/project/${item.session_id}/summary/generate`);
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

      {/* ================= GENERATION HISTORY ================= */}
      <h1 className={styles.title}>Generation History</h1>

      <div className={styles.grid}>
        {generation_history.map((item) => (
          <div
            key={item.session_id}
            className={styles.expandCard}
            style={{ cursor: "pointer" }}
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
                  <p>Create: {formatDateTime(item.created_at)}</p>
                  <p>Finish: {formatDateTime(item.generation_finished_at)}</p>
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

      {showDeleteModal && (
        <SharePopUpDelete
          isOpen={showDeleteModal}
          onClose={() => {
            setShowDeleteModal(false);
            setSelectedId(null);
          }}
          onConfirm={handleConfirmDelete}
          isLoading={isDeleting}
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
