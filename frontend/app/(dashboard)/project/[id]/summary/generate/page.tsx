"use client";

import { useParams, useRouter } from "next/navigation";
import { useQuery, useMutation } from "@tanstack/react-query";
import { clientFetch } from "@/lib/client-fetch";
import {
  ChevronLeft,
  Sparkles,
  Film,
  Check,
  X,
  User,
  ImageIcon,
  MessageSquare,
} from "lucide-react";
import { useState, useEffect } from "react";
import styles from "./page.module.css";

import SharePopUpSuccess from "@/components/SharePopUp_Success";
import SharePopUpFailed from "@/components/SharePopUp_Failed";

interface SummaryResponse {
  details: { session_name: string };
  summary: {
    sentence_count: number;
    character_count: number;
    scene_count: number;
    total_credit_required: number;
    credits_remaining: number;
  };
  status: string;
}

const DEMO_CREDIT = 10;

export default function GenerateSummaryPage() {
  const router = useRouter();
  const params = useParams();
  const sessionId = params.id as string;

  const [showSuccess, setShowSuccess] = useState(false);
  const [showFailed, setShowFailed] = useState(false);
  const [sessionName, setSessionName] = useState("");
  const [originalName, setOriginalName] = useState("");
  const [nameChanged, setNameChanged] = useState(false);

  const { data, isLoading, refetch } = useQuery<SummaryResponse>({
    queryKey: ["generateSummary", sessionId],
    queryFn: async () => {
      const res = await clientFetch(
        `/api/project/${sessionId}/summary/generate`,
      );
      if (!res.ok) throw new Error("Failed to fetch summary");
      return res.json();
    },
  });

  useEffect(() => {
    if (data) {
      setSessionName(data.details.session_name);
      setOriginalName(data.details.session_name);
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

  const generateMutation = useMutation({
    mutationFn: async () => {
      const res = await clientFetch(`/api/project/${sessionId}/generate`, {
        method: "POST",
      });
      if (!res.ok) throw new Error("Generate failed");
      return res.json();
    },
    onSuccess: () => setShowSuccess(true),
    onError: () => setShowFailed(true),
  });

  if (isLoading || !data) {
    return (
      <div className={styles.loadingState}>
        <div className={styles.loadingBar}>
          <div className={styles.loadingFill} />
        </div>
        <span>Loading Summary...</span>
      </div>
    );
  }

  const { summary } = data;
  const notEnoughCredit =
    summary.credits_remaining < summary.total_credit_required;
  const notEnoughDemoCredit = summary.credits_remaining < DEMO_CREDIT;

  const ASSET_ROWS = [
    {
      icon: <MessageSquare size={14} />,
      label: "Narrator Voice",
      value: summary.sentence_count,
      color: "blue",
    },
    {
      icon: <User size={14} />,
      label: "Character Images",
      value: summary.character_count,
      color: "purple",
    },
    {
      icon: <ImageIcon size={14} />,
      label: "Scene Images",
      value: summary.scene_count,
      color: "teal",
    },
  ];

  return (
    <div className={styles.container}>
      {/* ── Header ── */}
      <header className={styles.header}>
        <button onClick={() => router.back()} className={styles.backBtn}>
          <ChevronLeft size={20} />
        </button>
        <div>
          <h1 className={styles.title}>New Video</h1>
          <p className={styles.subtitle}>
            Review assets and launch AI video generation
          </p>
        </div>
      </header>

      {/* ── Session name ── */}
      <div className={styles.configBlock}>
        <label className={styles.configLabel}>Video Title</label>
        <div className={styles.nameRow}>
          <input
            value={sessionName}
            onChange={(e) => {
              setSessionName(e.target.value);
              setNameChanged(e.target.value !== originalName);
            }}
            className={styles.nameInput}
            placeholder="Enter video name…"
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

      {/* ── Main card ── */}
      <div className={styles.card}>
        {/* LEFT — asset summary */}
        <div className={styles.summarySection}>
          <div className={styles.sectionHead}>
            <Film size={14} className={styles.sectionIcon} />
            <span className={styles.sectionTitle}>Asset Summary</span>
          </div>

          <div className={styles.assetList}>
            {ASSET_ROWS.map(({ icon, label, value, color }) => (
              <div
                key={label}
                className={`${styles.assetRow} ${styles[`assetRow_${color}`]}`}
              >
                <div
                  className={`${styles.assetIcon} ${styles[`assetIcon_${color}`]}`}
                >
                  {icon}
                </div>
                <span className={styles.assetLabel}>{label}</span>
                <span className={styles.assetValue}>
                  {value.toLocaleString()}
                </span>
              </div>
            ))}
          </div>

          <div className={styles.creditRows}>
            <div className={styles.summaryDivider} />
            <div className={`${styles.creditRow} ${styles.creditTotal}`}>
              <span className={styles.creditKey}>Total credits required</span>
              <span className={styles.creditValBig}>
                {summary.total_credit_required.toLocaleString()}
              </span>
            </div>
            <div
              className={`${styles.creditRow} ${notEnoughCredit ? styles.creditLow : styles.creditOk}`}
            >
              <span className={styles.creditKey}>Your balance</span>
              <span className={styles.creditValBig}>
                {summary.credits_remaining.toLocaleString()}
              </span>
            </div>
          </div>
        </div>

        {/* RIGHT — actions */}
        <div className={styles.actionSection}>
          <div className={styles.sectionHead}>
            <span className={styles.sectionTitle}>Launch</span>
          </div>

          <div className={styles.actionPad}>
            {/* Demo button */}
            <div className={styles.demoWrap}>
              <button
                className={styles.demoBtn}
                disabled={generateMutation.isPending || notEnoughDemoCredit}
              >
                <Sparkles size={14} />
                {generateMutation.isPending ? "Generating…" : "Generate Demo"}
              </button>
              <span className={styles.demoNote}>
                {DEMO_CREDIT} credits · short preview
              </span>
            </div>

            <div className={styles.orDivider}>
              <span>or</span>
            </div>

            {/* Full generate */}
            <button
              className={styles.generateBtn}
              onClick={() => generateMutation.mutate()}
              disabled={generateMutation.isPending || notEnoughCredit}
            >
              {generateMutation.isPending ? (
                <>
                  <span className={styles.btnSpinner} /> Generating…
                </>
              ) : (
                <>
                  <Sparkles size={17} /> Generate Full ·{" "}
                  {summary.total_credit_required.toLocaleString()} Credits
                </>
              )}
            </button>

            {notEnoughCredit && (
              <p className={styles.warning}>
                Insufficient credits — top up to continue.
              </p>
            )}
          </div>
        </div>
      </div>

      <SharePopUpSuccess
        isOpen={showSuccess}
        title="Generation started!"
        message="Your video is being generated. Check the project page for updates."
        onClose={() => {
          setShowSuccess(false);
          router.push("/project");
        }}
      />
      <SharePopUpFailed
        isOpen={showFailed}
        title="Generation failed"
        message="Unable to start video generation. Please try again."
        onClose={() => setShowFailed(false)}
      />
    </div>
  );
}
