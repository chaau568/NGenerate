"use client";

import { useEffect, useState } from "react";
import { useRouter, useParams } from "next/navigation";
import { clientFetch } from "@/lib/client-fetch";
import SharePopUpAction from "@/components/SharePopUp_Action";
import { Save, Edit3, Trash2, X, ChevronLeft, Sparkles } from "lucide-react";
import SharePopUpDelete from "@/components/SharePopUp_Delete";
import styles from "./page.module.css";

interface ChapterData {
  id: number;
  title: string;
  story: string;
  is_analyzed: boolean;
}

export default function ChapterDetailPage() {
  const router = useRouter();
  const params = useParams();
  const chapterId = params?.chapterId;
  const novelId = params?.id;

  const [savedData, setSavedData] = useState<ChapterData | null>(null);
  const [currentData, setCurrentData] = useState<ChapterData | null>(null);
  const [isEditing, setIsEditing] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);

  const [isCreating, setIsCreating] = useState(false);
  const [showSessionModal, setShowSessionModal] = useState(false);
  const [showFailedModal, setShowFailedModal] = useState(false);
  const [createdSessionId, setCreatedSessionId] = useState<number | null>(null);

  useEffect(() => {
    if (chapterId) fetchChapter();
  }, [chapterId]);

  const fetchChapter = async () => {
    const res = await clientFetch(`/api/library/chapters/${chapterId}`);
    if (res.ok) {
      const data = await res.json();
      setSavedData(data);
      setCurrentData(data);
    }
  };

  const handleAnalyze = async () => {
    setIsCreating(true);
    try {
      const res = await clientFetch(`/api/project/${novelId}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          chapter_ids: [Number(chapterId)],
          session_type: "analysis",
        }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data?.detail || "");
      setCreatedSessionId(data.id || data.session_id);
      setShowSessionModal(true);
    } catch {
      setShowFailedModal(true);
    } finally {
      setIsCreating(false);
    }
  };

  const hasChanges = JSON.stringify(savedData) !== JSON.stringify(currentData);

  const handleSave = async () => {
    if (!hasChanges || isSaving) return;
    setIsSaving(true);
    const res = await clientFetch(`/api/library/chapters/${chapterId}`, {
      method: "PUT",
      body: JSON.stringify({
        title: currentData?.title,
        story: currentData?.story,
      }),
    });
    if (res.ok) {
      const updated = await res.json();
      setSavedData(updated);
      setIsEditing(false);
    }
    setIsSaving(false);
  };

  const handleCancel = () => {
    setCurrentData(savedData);
    setIsEditing(false);
  };

  const handleDelete = async () => {
    setIsDeleting(true);
    try {
      const res = await clientFetch(`/api/library/chapters/${chapterId}`, {
        method: "DELETE",
      });
      if (res.ok) router.push(`/library/${novelId}`);
      else alert("Failed to delete chapter");
    } catch (e) {
      console.error(e);
    } finally {
      setIsDeleting(false);
      setShowDeleteModal(false);
    }
  };

  if (!currentData)
    return (
      <div className={styles.loadingState}>
        <div className={styles.loadingBar}>
          <div className={styles.loadingFill} />
        </div>
        <span>Loading Chapter…</span>
      </div>
    );

  const wordCount = currentData.story.trim()
    ? currentData.story.trim().split(/\s+/).length
    : 0;

  return (
    <div className={styles.container}>
      {/* ── HEADER ── */}
      <header className={styles.header}>
        <button onClick={() => router.back()} className={styles.backBtn}>
          <ChevronLeft size={18} />
        </button>

        <div className={styles.headerMeta}>
          {currentData.is_analyzed && (
            <span className={styles.analyzedChip}>Analyzed</span>
          )}
          {isEditing && hasChanges && (
            <span className={styles.unsavedChip}>Unsaved changes</span>
          )}
        </div>

        <div className={styles.toolbar}>
          {!isEditing ? (
            <>
              <button
                className={styles.editBtn}
                onClick={() => setIsEditing(true)}
              >
                <Edit3 size={14} /> Edit
              </button>
              <button
                className={styles.dangerBtn}
                onClick={() => setShowDeleteModal(true)}
              >
                <Trash2 size={14} />
              </button>
            </>
          ) : (
            <>
              <button
                className={`${styles.saveBtn} ${hasChanges ? styles.saveBtnActive : ""}`}
                onClick={handleSave}
                disabled={!hasChanges || isSaving}
              >
                <Save size={14} /> {isSaving ? "Saving..." : "Save"}
              </button>
              <button className={styles.cancelBtn} onClick={handleCancel}>
                <X size={14} />
              </button>
            </>
          )}
        </div>
      </header>
      {/* ── EDITOR ── */}
      <main className={styles.editor}>
        <input
          className={`${styles.titleInput} ${isEditing ? styles.titleInputEditing : ""}`}
          value={currentData.title}
          onChange={(e) =>
            setCurrentData({ ...currentData, title: e.target.value })
          }
          disabled={!isEditing}
          placeholder="Chapter Title"
        />

        <div className={styles.storyWrap}>
          <textarea
            className={`${styles.storyArea} ${isEditing ? styles.storyAreaEditing : ""}`}
            value={currentData.story}
            onChange={(e) =>
              setCurrentData({ ...currentData, story: e.target.value })
            }
            disabled={!isEditing}
            placeholder="Write your story here..."
          />
        </div>

        <div className={styles.editorFooterBar}>
          <span className={styles.wordCount}>
            {wordCount.toLocaleString()} words
          </span>
        </div>
      </main>
      {/* ── FOOTER CTA ── */}
      <footer className={styles.footer}>
        <button
          className={styles.analyzeBtn}
          onClick={handleAnalyze}
          disabled={isCreating}
        >
          <Sparkles size={15} />
          {isCreating ? "Creating..." : "Analyze From This Chapter"}
        </button>
      </footer>
      {showDeleteModal && (
        <SharePopUpDelete
          isOpen={showDeleteModal}
          onClose={() => setShowDeleteModal(false)}
          onConfirm={handleDelete}
          isLoading={isDeleting}
          title="Delete Chapter?"
          description={
            <p>
              Delete <strong>"{currentData.title}"</strong>? This cannot be
              undone.
            </p>
          }
        />
      )}

      <SharePopUpAction
        isOpen={showSessionModal}
        type="success"
        title="Project Created!"
        description="Analysis session is ready."
        primaryText="Go to Project"
        secondaryText="Close"
        onPrimary={() => {
          if (createdSessionId)
            router.push(`/project/${createdSessionId}/summary/analyze`);
        }}
        onSecondary={() => setShowSessionModal(false)}
        onClose={() => setShowSessionModal(false)}
      />
      <SharePopUpAction
        isOpen={showFailedModal}
        type="error"
        title="Something went wrong"
        description="Unable to create project. Please try again."
        primaryText="Try Again"
        secondaryText="Close"
        onPrimary={() => setShowFailedModal(false)}
        onSecondary={() => setShowFailedModal(false)}
        onClose={() => setShowFailedModal(false)}
      />
    </div>
  );
}
