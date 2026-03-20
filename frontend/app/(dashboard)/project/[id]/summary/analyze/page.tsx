"use client";

import { useParams, useRouter } from "next/navigation";
import { useQuery, useMutation } from "@tanstack/react-query";
import { clientFetch } from "@/lib/client-fetch";
import SharePopUp_Action from "@/components/SharePopUp_Action";
import SharePopUpFailed from "@/components/SharePopUp_Failed";
import {
  ChevronLeft,
  Trash2,
  Sparkles,
  BookOpen,
  Palette,
  Check,
  X,
} from "lucide-react";
import { useState, useEffect, useRef } from "react";
import styles from "./page.module.css";

interface Chapter {
  id: number;
  order: number;
  title: string;
}
interface StyleChoice {
  value: string;
  label: string;
}
interface AnalyzeResponse {
  details: { session_name: string; style: string; chapters: Chapter[] };
  summary: {
    session_type: string;
    chapter_count: number;
    credit_per_chapter: number;
    total_credit_required: number;
    credits_remaining: number;
  };
  style_choices: StyleChoice[];
  status: string;
}

export default function AnalyzeSummaryPage() {
  const router = useRouter();
  const params = useParams();
  const sessionId = params.id as string;

  const [sessionName, setSessionName] = useState("");
  const [style, setStyle] = useState("");
  const [styleChoices, setStyleChoices] = useState<StyleChoice[]>([]);
  const [originalName, setOriginalName] = useState("");
  const [chapters, setChapters] = useState<Chapter[]>([]);
  const [nameChanged, setNameChanged] = useState(false);
  const [analysisStarted, setAnalysisStarted] = useState(false);
  const analysisStartedRef = useRef(false);
  const statusRef = useRef<string | null>(null);

  const [showErrorPopup, setShowErrorPopup] = useState(false);
  const [errorContent, setErrorContent] = useState({ title: "", message: "" });

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
      setStyle(data.details.style);
      setStyleChoices(data.style_choices);
      statusRef.current = data.status;
    }
  }, [data]);

  useEffect(() => {
    analysisStartedRef.current = analysisStarted;
  }, [analysisStarted]);

  useEffect(() => {
    return () => {
      if (statusRef.current === "draft" && !analysisStartedRef.current) {
        fetch(`/api/project/${sessionId}`, {
          method: "DELETE",
          keepalive: true,
        });
      }
    };
  }, [sessionId]);

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
      setAnalysisStarted(true);
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

  if (isLoading || !data) {
    return (
      <div className={styles.loadingState}>
        <div className={styles.loadingBar}>
          <div className={styles.loadingFill} />
        </div>
        <span>Loading Summary…</span>
      </div>
    );
  }

  const { summary } = data;
  const notEnoughCredit =
    summary.credits_remaining < summary.total_credit_required;

  return (
    <div className={styles.container}>
      {/* ── Header ── */}
      <header className={styles.header}>
        <button onClick={() => router.back()} className={styles.backBtn}>
          <ChevronLeft size={20} />
        </button>
        <div>
          <h1 className={styles.title}>New Analysis</h1>
          <p className={styles.subtitle}>
            Configure and launch your AI analysis session
          </p>
        </div>
      </header>

      {/* ── Session config ── */}
      <div className={styles.configRow}>
        {/* Name */}
        <div className={styles.configBlock}>
          <label className={styles.configLabel}>Session Title</label>
          <div className={styles.nameRow}>
            <input
              value={sessionName}
              onChange={(e) => {
                setSessionName(e.target.value);
                setNameChanged(e.target.value !== originalName);
              }}
              className={styles.nameInput}
              placeholder="Enter session name…"
            />
            {nameChanged && (
              <div className={styles.nameActions}>
                <button
                  className={styles.nameCancel}
                  onClick={() => {
                    setSessionName(originalName);
                    setNameChanged(false);
                  }}
                  disabled={editMutation.isPending}
                >
                  <X size={14} />
                </button>
                <button
                  className={styles.nameConfirm}
                  onClick={() => editMutation.mutate({ name: sessionName })}
                  disabled={editMutation.isPending}
                >
                  <Check size={14} />
                </button>
              </div>
            )}
          </div>
        </div>

        {/* Style */}
        <div className={styles.configBlock}>
          <label className={styles.configLabel}>
            <Palette size={12} /> Visual Style
          </label>
          <div className={styles.styleGrid}>
            {styleChoices.map((s) => (
              <button
                key={s.value}
                className={`${styles.styleChip} ${style === s.value ? styles.styleChipActive : ""}`}
                onClick={() => {
                  setStyle(s.value);
                  editMutation.mutate({ style: s.value });
                }}
              >
                {s.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* ── Main card ── */}
      <div className={styles.card}>
        {/* LEFT — chapter list */}
        <div className={styles.chapterSection}>
          <div className={styles.sectionHead}>
            <div className={styles.sectionHeadLeft}>
              <BookOpen size={15} className={styles.sectionIcon} />
              <span className={styles.sectionTitle}>Selected Chapters</span>
            </div>
            <span className={styles.countBadge}>{chapters.length}</span>
          </div>

          <div className={styles.chapterList}>
            {chapters.map((chapter) => (
              <div key={chapter.id} className={styles.chapterCard}>
                <div className={styles.chapterInfo}>
                  <span className={styles.chapterOrder}>
                    Ch. {chapter.order}
                  </span>
                  <span className={styles.chapterTitle}>{chapter.title}</span>
                </div>
                <button
                  className={styles.deleteBtn}
                  onClick={() => {
                    if (chapters.length <= 1) {
                      setErrorContent({
                        title: "Minimum Chapters Required",
                        message:
                          "Your analysis must include at least one chapter. You cannot delete the last one.",
                      });
                      setShowErrorPopup(true);
                      return;
                    }

                    const updated = chapters.filter((c) => c.id !== chapter.id);
                    setChapters(updated);
                    editMutation.mutate({
                      chapter_ids: updated.map((c) => c.id),
                    });
                  }}
                  disabled={editMutation.isPending}
                >
                  <Trash2 size={32} />
                </button>
              </div>
            ))}
          </div>
        </div>

        {/* RIGHT — summary + CTA */}
        <div className={styles.actionSection}>
          <div className={styles.sectionHead}>
            <span className={styles.sectionTitle}>Cost Summary</span>
          </div>

          <div className={styles.summaryList}>
            <div className={styles.summaryRow}>
              <span className={styles.summaryKey}>Type</span>
              <span className={styles.summaryVal}>Analysis</span>
            </div>
            <div className={styles.summaryRow}>
              <span className={styles.summaryKey}>Chapters</span>
              <span className={styles.summaryVal}>{summary.chapter_count}</span>
            </div>
            <div className={styles.summaryRow}>
              <span className={styles.summaryKey}>Credits / chapter</span>
              <span className={styles.summaryVal}>
                {summary.credit_per_chapter}
              </span>
            </div>

            <div className={styles.summaryDivider} />

            <div className={`${styles.summaryRow} ${styles.summaryTotal}`}>
              <span className={styles.summaryKey}>Total required</span>
              <span className={styles.summaryValBig}>
                {summary.total_credit_required}
              </span>
            </div>
            <div
              className={`${styles.summaryRow} ${notEnoughCredit ? styles.summaryLow : styles.summaryOk}`}
            >
              <span className={styles.summaryKey}>Your balance</span>
              <span className={styles.summaryValBig}>
                {summary.credits_remaining.toLocaleString()}
              </span>
            </div>
          </div>

          {notEnoughCredit && (
            <p className={styles.warning}>
              Insufficient credits — top up to continue.
            </p>
          )}

          <button
            className={styles.analyzeBtn}
            disabled={
              notEnoughCredit ||
              editMutation.isPending ||
              analyzeMutation.isPending
            }
            onClick={() => analyzeMutation.mutate()}
          >
            {analyzeMutation.isPending ? (
              <>
                <span className={styles.btnSpinner} /> Starting…
              </>
            ) : (
              <>
                <Sparkles size={17} /> Analyze · {summary.total_credit_required}{" "}
                Credits
              </>
            )}
          </button>
        </div>
      </div>

      <SharePopUpFailed
        isOpen={showErrorPopup}
        onClose={() => setShowErrorPopup(false)}
        title={errorContent.title}
        message={errorContent.message}
      />

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
            if (popup.type === "success") router.push("/project");
            else setPopup({ type: null });
          }}
          onSecondary={() => setPopup({ type: null })}
          onClose={() => setPopup({ type: null })}
        />
      )}
    </div>
  );
}
