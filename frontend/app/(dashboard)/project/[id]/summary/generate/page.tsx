"use client";

import { useParams, useRouter } from "next/navigation";
import { useQuery, useMutation } from "@tanstack/react-query";
import { clientFetch } from "@/lib/client-fetch";
import { ChevronLeft } from "lucide-react";
import { useState, useEffect } from "react";
import styles from "./page.module.css";

import SharePopUpSuccess from "@/components/SharePopUp_Success";
import SharePopUpFailed from "@/components/SharePopUp_Failed";

interface SummaryResponse {
  details: {
    session_name: string;
  };
  summary: {
    sentence_count: number;
    character_count: number;
    scene_count: number;
    total_credit_required: number;
    credits_remaining: number;
  };
  status: string;
}

export default function GenerateSummaryPage() {
  const router = useRouter();
  const params = useParams();
  const sessionId = params.id as string;

  const [showSuccess, setShowSuccess] = useState(false);
  const [showFailed, setShowFailed] = useState(false);

  // State สำหรับการแก้ไขชื่อ
  const [sessionName, setSessionName] = useState("");
  const [originalName, setOriginalName] = useState("");
  const [nameChanged, setNameChanged] = useState(false);

  /* ================= FETCH SUMMARY ================= */

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

  /* ================= EDIT NAME MUTATION ================= */

  const editMutation = useMutation({
    mutationFn: async (payload: any) => {
      // ใช้ endpoint เดียวกันกับ analyze ตามที่กำหนด
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

  const handleConfirmName = () => {
    editMutation.mutate({ name: sessionName });
  };

  const handleCancelName = () => {
    setSessionName(originalName);
    setNameChanged(false);
  };

  /* ================= GENERATE ================= */

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
    return <div className={styles.loading}>Loading summary...</div>;
  }

  const { summary } = data;
  const DEMO_CREDIT = 10;
  const notEnoughCredit =
    summary.credits_remaining < summary.total_credit_required;
  const notEnoughDemoCredit = summary.credits_remaining < DEMO_CREDIT;

  return (
    <div className={styles.container}>
      <header className={styles.header}>
        <div className={styles.headerLeft}>
          <button onClick={() => router.back()} className={styles.backBtn}>
            <ChevronLeft size={22} />
          </button>
          <h1>Create New Video</h1>
        </div>
      </header>

      {/* ================= Editable Session Name (Modern Style) ================= */}
      <div className={styles.sessionWrapper}>
        <div className={styles.labelTitle}>Video Title</div>
        <div className={styles.sessionEditRow}>
          <input
            value={sessionName}
            onChange={(e) => {
              setSessionName(e.target.value);
              setNameChanged(e.target.value !== originalName);
            }}
            className={styles.sessionInput}
            placeholder="Enter video name..."
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
        {/* ================= LEFT ================= */}
        <div className={styles.summarySection}>
          <h2>Summary</h2>
          <div className={styles.summaryGrid}>
            <div>
              <p>Sentence Assets</p>
              <strong>{summary.sentence_count}</strong>
            </div>
            <div>
              <p>Image Assets (Character)</p>
              <strong>{summary.character_count}</strong>
            </div>
            <div>
              <p>Image Assets (Scene)</p>
              <strong>{summary.scene_count}</strong>
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
        </div>

        {/* ================= RIGHT ================= */}
        <div className={styles.actionSection}>
          <button
            className={styles.demoBtn}
            disabled={generateMutation.isPending || notEnoughDemoCredit}
          >
            {generateMutation.isPending
              ? "Generating..."
              : `Generate Demo (10 Credits)`}
          </button>

          <button
            className={styles.generateBtn}
            onClick={() => generateMutation.mutate()}
            disabled={generateMutation.isPending || notEnoughCredit}
          >
            {generateMutation.isPending
              ? "Generating..."
              : `Generate (${summary.total_credit_required} Credits)`}
          </button>

          {notEnoughCredit && (
            <p className={styles.warning}>
              Not enough credits to generate this video.
            </p>
          )}
        </div>
      </div>

      <SharePopUpSuccess
        isOpen={showSuccess}
        title="Video generation started successfully!"
        onClose={() => {
          setShowSuccess(false);
          router.push("/project");
        }}
      />

      <SharePopUpFailed
        isOpen={showFailed}
        title="Generation Failed"
        message="Unable to start video generation. Please try again."
        onClose={() => setShowFailed(false)}
      />
    </div>
  );
}
