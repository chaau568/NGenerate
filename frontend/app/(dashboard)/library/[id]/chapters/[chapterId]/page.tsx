"use client";

import { useEffect, useState, use } from "react";
import { useRouter, useParams } from "next/navigation";
import { clientFetch } from "@/lib/client-fetch";
import {
  Save,
  Edit3,
  Trash2,
  X,
  ChevronLeft,
  Sparkles,
  AlertTriangle,
} from "lucide-react";
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
      if (res.ok) {
        router.push(`/library/${novelId}`);
      } else {
        alert("Failed to delete chapter");
      }
    } catch (error) {
      console.error(error);
    } finally {
      setIsDeleting(false);
      setShowDeleteModal(false);
    }
  };

  if (!currentData) return <div className={styles.loading}>Loading...</div>;

  return (
    <div className={styles.container}>
      <header className={styles.header}>
        <button onClick={() => router.back()} className={styles.backBtn}>
          <ChevronLeft size={22} />
        </button>

        <div className={styles.toolbar}>
          {!isEditing ? (
            <>
              <button
                className={styles.editBtn}
                onClick={() => setIsEditing(true)}
              >
                <Edit3 size={18} /> Edit
              </button>
              <button
                className={styles.deleteBtn}
                onClick={() => setShowDeleteModal(true)}
              >
                <Trash2 size={18} /> Delete
              </button>
            </>
          ) : (
            <>
              <button
                className={`${styles.saveBtn} ${hasChanges ? styles.active : ""}`}
                onClick={handleSave}
                disabled={!hasChanges || isSaving}
              >
                <Save size={18} /> {isSaving ? "Saving..." : "Save"}
              </button>
              <button className={styles.cancelBtn} onClick={handleCancel}>
                <X size={18} /> Cancel
              </button>
            </>
          )}
        </div>
      </header>

      <main className={styles.editorContainer}>
        <input
          className={styles.titleInput}
          value={currentData.title}
          onChange={(e) =>
            setCurrentData({ ...currentData, title: e.target.value })
          }
          disabled={!isEditing}
          placeholder="Chapter Title"
        />

        <textarea
          className={styles.storyArea}
          value={currentData.story}
          onChange={(e) =>
            setCurrentData({ ...currentData, story: e.target.value })
          }
          disabled={!isEditing}
          placeholder="Write your story here..."
        />
      </main>

      <footer className={styles.footer}>
        <button className={styles.analyzeBtn}>
          <Sparkles size={20} />
          Analyze From This Chapter
        </button>
      </footer>
      {showDeleteModal && (
        <div className={styles.modalOverlay}>
          <div className={styles.modalContent}>
            <div className={styles.modalIcon}>
              <AlertTriangle size={48} color="#ef4444" />
            </div>
            <h3>Delete Chapter?</h3>
            <p>
              Are you sure you want to delete{" "}
              <strong>"{currentData.title}"</strong>? This action cannot be
              undone.
            </p>
            <div className={styles.modalActions}>
              <button
                className={styles.modalCancelBtn}
                onClick={() => setShowDeleteModal(false)}
                disabled={isDeleting}
              >
                Cancel
              </button>
              <button
                className={styles.confirmDeleteBtn}
                onClick={handleDelete}
                disabled={isDeleting}
              >
                {isDeleting ? "Deleting..." : "Delete Permanently"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
