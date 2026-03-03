"use client";

import { useParams, useRouter } from "next/navigation";
import { useQuery, useMutation } from "@tanstack/react-query";
import { clientFetch } from "@/lib/client-fetch";
import SharePopUp_Action from "@/components/SharePopUp_Action";
import { ChevronLeft, Trash2, Plus, Star } from "lucide-react";
import { useState, useEffect } from "react";
import styles from "./page.module.css";

interface Chapter {
  id: number;
  order: number;
  title: string;
}

interface AnalyzeResponse {
  details: {
    session_name: string;
    chapters: Chapter[];
  };
  summary: {
    session_type: string;
    chapter_count: number;
    credit_per_chapter: number;
    total_credit_required: number;
    credits_remaining: number;
  };
  status: string;
}

export default function AnalyzeSummaryPage() {
  const router = useRouter();
  const params = useParams();
  const sessionId = params.id as string;

  const [sessionName, setSessionName] = useState("");
  const [originalName, setOriginalName] = useState("");
  const [chapters, setChapters] = useState<Chapter[]>([]);
  const [nameChanged, setNameChanged] = useState(false);

  const [popup, setPopup] = useState<{
    type: "success" | "error" | null;
    message?: string;
  }>({ type: null });

  const { data, isLoading, refetch } = useQuery<AnalyzeResponse>({
    queryKey: ["analyzeSummary", sessionId],
    queryFn: async () => {
      const res = await clientFetch(
        `/api/project/${sessionId}/summary/analyze`,
      );
      if (!res.ok) throw new Error("Failed");
      return res.json();
    },
  });

  useEffect(() => {
    if (data) {
      setSessionName(data.details.session_name);
      setOriginalName(data.details.session_name);
      setChapters(data.details.chapters);
    }
  }, [data]);

  const editMutation = useMutation({
    mutationFn: async (payload: any) => {
      const res = await clientFetch(
        `/api/project/${sessionId}/summary/analyze`,
        {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        },
      );
      if (!res.ok) throw new Error("Edit failed");
      return res.json();
    },
    onSuccess: () => {
      refetch();
      setNameChanged(false);
    },
  });

  const handleRemoveChapter = (id: number) => {
    const updated = chapters.filter((c) => c.id !== id);
    setChapters(updated);
    editMutation.mutate({ chapter_ids: updated.map((c) => c.id) });
  };

  const handleConfirmName = () => {
    editMutation.mutate({ name: sessionName });
  };

  const handleCancelName = () => {
    setSessionName(originalName);
    setNameChanged(false);
  };

  const analyzeMutation = useMutation({
    mutationFn: async () => {
      const res = await clientFetch(`/api/project/${sessionId}/analyze`, {
        method: "POST",
      });

      if (!res.ok) {
        const err = await res.json().catch(() => null);
        throw new Error(err?.message || "Analyze failed");
      }

      return res.json();
    },
    onSuccess: () => {
      setPopup({
        type: "success",
        message: "Your analysis has started successfully.",
      });
    },
    onError: (error: any) => {
      setPopup({
        type: "error",
        message: error.message || "Something went wrong.",
      });
    },
  });

  if (isLoading || !data)
    return <div className={styles.loading}>Loading summary...</div>;

  const { summary } = data;
  const notEnoughCredit =
    summary.credits_remaining < summary.total_credit_required;

  return (
    <div className={styles.container}>
      <header className={styles.header}>
        <div className={styles.headerLeft}>
          <button onClick={() => router.back()} className={styles.backBtn}>
            <ChevronLeft size={22} />
          </button>
          <h1>Create New Analysis</h1>
        </div>
      </header>

      {/* Title & Editable Name */}
      <div className={styles.sessionWrapper}>
        <div className={styles.labelTitle}>Analysis Title</div>
        <div className={styles.sessionEditRow}>
          <input
            value={sessionName}
            onChange={(e) => {
              setSessionName(e.target.value);
              setNameChanged(e.target.value !== originalName);
            }}
            className={styles.sessionInput}
            placeholder="Enter session name..."
          />

          <div className={styles.actionButtons}>
            <button
              className={styles.cancelBtn}
              onClick={handleCancelName}
              disabled={!nameChanged || editMutation.isPending}
            >
              Cancel
            </button>
            <button
              className={styles.confirmBtn}
              onClick={handleConfirmName}
              disabled={!nameChanged || editMutation.isPending}
            >
              Confirm
            </button>
          </div>
        </div>
      </div>

      <div className={styles.card}>
        {/* LEFT: Chapter Selection List */}
        <div className={styles.chapterSection}>
          <div className={styles.chapterHeaderRow}>
            <h2>
              Selected Chapters{" "}
              <span className={styles.countBadge}>{chapters.length}</span>
            </h2>
            {/* <button className={styles.addChapterBtn}>
              <Plus size={16} /> Add New Chapter
            </button> */}
          </div>

          <div className={styles.chapterList}>
            {chapters.map((chapter) => (
              <div key={chapter.id} className={styles.chapterCard}>
                <div className={styles.chapterInfo}>
                  <p className={styles.chapterLabel}>Chapter {chapter.order}</p>
                  <p className={styles.chapterName}>{chapter.title}</p>
                </div>
                <button
                  className={styles.deleteBtn}
                  onClick={() => handleRemoveChapter(chapter.id)}
                  disabled={editMutation.isPending}
                >
                  <Trash2 size={16} />
                </button>
              </div>
            ))}
          </div>
        </div>

        {/* RIGHT: Summary & Action */}
        <div className={styles.actionSection}>
          <h2>Summary</h2>
          <div className={styles.summaryGrid}>
            <div>
              <p>Type</p>
              <strong>Analysis</strong>
            </div>
            <div>
              <p>Chapter Count</p>
              <strong>{summary.chapter_count}</strong>
            </div>
            <div>
              <p>Credits per Chapter</p>
              <strong>{summary.credit_per_chapter}</strong>
            </div>
            <div className={styles.total}>
              <p>Total Credits Required</p>
              <strong>{summary.total_credit_required}</strong>
            </div>
            <div className={styles.remaining}>
              <p>Credits Remaining</p>
              <strong>{summary.credits_remaining.toLocaleString()}</strong>
            </div>
          </div>

          <button
            className={styles.analyzeBtn}
            disabled={
              notEnoughCredit ||
              editMutation.isPending ||
              analyzeMutation.isPending
            }
            onClick={() => analyzeMutation.mutate()}
          >
            <Star size={20} fill="currentColor" />
            <span>
              {analyzeMutation.isPending
                ? "Starting..."
                : `Analyze (${summary.total_credit_required} Credits)`}
            </span>
          </button>
          {notEnoughCredit && (
            <p className={styles.warning}>
              Not enough credits for this analysis.
            </p>
          )}
        </div>
      </div>
      {popup.type && (
        <SharePopUp_Action
          isOpen={true}
          type={popup.type}
          title={
            popup.type === "success" ? "Analysis Started" : "Analysis Failed"
          }
          description={popup.message}
          primaryText={
            popup.type === "success" ? "Go to Projects" : "Try Again"
          }
          secondaryText={popup.type === "error" ? "Close" : undefined}
          onPrimary={() => {
            if (popup.type === "success") {
              router.push("/project");
            } else {
              setPopup({ type: null });
            }
          }}
          onSecondary={() => setPopup({ type: null })}
          onClose={() => setPopup({ type: null })}
        />
      )}
    </div>
  );
}
