"use client";

import { clientFetch } from "@/lib/client-fetch";
import { useEffect, useState, useRef } from "react";
import { useRouter, useParams } from "next/navigation";
import {
  Plus,
  Trash2,
  CheckCircle2,
  Pencil,
  FileText,
  UploadCloud,
  X,
  ChevronLeft,
  Users,
  Zap,
} from "lucide-react";
import SharePopUpDelete from "@/components/SharePopUp_Delete";
import SharePopUpAction from "@/components/SharePopUp_Action";
import styles from "./page.module.css";
import Image from "next/image";

interface Character {
  name: string;
  master_image_path: string | null;
}
interface Chapter {
  id: number;
  order: number;
  title: string;
  is_analyzed: boolean;
}
interface NovelDetail {
  id: number;
  title: string;
  cover: string | null;
  chapters: Chapter[];
  characters: Character[];
}

export default function NovelDetailPage() {
  const router = useRouter();
  const params = useParams();
  const id = Array.isArray(params?.id) ? params.id[0] : params?.id;

  const [novel, setNovel] = useState<NovelDetail | null>(null);
  const [selectedChapters, setSelectedChapters] = useState<number[]>([]);
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const [showAddModal, setShowAddModal] = useState(false);
  const [addMode, setAddMode] = useState<"text" | "file" | null>(null);
  const [storyText, setStoryText] = useState("");
  const [isUploading, setIsUploading] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [showSuccessModal, setShowSuccessModal] = useState(false);
  const [isCreating, setIsCreating] = useState(false);
  const [showSessionModal, setShowSessionModal] = useState(false);
  const [showFailedModal, setShowFailedModal] = useState(false);
  const [createdSessionId, setCreatedSessionId] = useState<number | null>(null);
  const [showEditModal, setShowEditModal] = useState(false);
  const [editTitle, setEditTitle] = useState("");
  const editFileRef = useRef<HTMLInputElement>(null);
  const [isSaving, setIsSaving] = useState(false);

  const [isFixing, setIsFixing] = useState(false);
  const [showFixSuccessModal, setShowFixSuccessModal] = useState(false);
  const CHAPTER_UNIT = 10;
  const costPerChapter = 0.25 / CHAPTER_UNIT;
  const totalFixCost = Math.ceil(selectedChapters.length * costPerChapter);

  useEffect(() => {
    if (!id) return;
    clientFetch(`/api/library/${id}`).then(async (res) => {
      if (!res.ok) {
        if (res.status === 401) {
          window.location.href = "/login";
          return;
        }
        throw new Error("");
      }
      const data = await res.json();
      setNovel({
        ...data,
        chapters: data.chapters ?? [],
        characters: data.characters ?? [],
      });
    });
  }, [id]);

  useEffect(() => {
    if (!showSuccessModal) return;
    const t = setTimeout(handleSuccessClose, 5000);
    return () => clearTimeout(t);
  }, [showSuccessModal]);

  const handleSuccessClose = () => {
    setShowSuccessModal(false);
    window.location.reload();
  };

  const toggleChapter = (chapterId: number) =>
    setSelectedChapters((prev) =>
      prev.includes(chapterId)
        ? prev.filter((i) => i !== chapterId)
        : [...prev, chapterId],
    );

  const handleSelectAll = () => {
    if (!novel) return;
    if (selectedChapters.length === novel.chapters.length)
      setSelectedChapters([]);
    else setSelectedChapters(novel.chapters.map((c) => c.id));
  };

  const handleAnalyze = async () => {
    if (selectedChapters.length === 0) return;
    setIsCreating(true);
    try {
      const res = await clientFetch(`/api/project/${id}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          chapter_ids: selectedChapters,
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

  const handleFixText = async () => {
    if (selectedChapters.length === 0) return;
    setIsFixing(true);
    try {
      const res = await clientFetch(`/api/library/${id}/fix-chapters`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          chapter_ids: selectedChapters,
        }),
      });

      if (res.ok) {
        setShowFixSuccessModal(true);
        setSelectedChapters([]);
      } else {
        const data = await res.json();
        alert(data.detail || "Failed to start fix text process");
      }
    } catch (err) {
      alert("Something went wrong");
    } finally {
      setIsFixing(false);
    }
  };

  const handleDelete = async () => {
    setIsDeleting(true);
    try {
      const res = await clientFetch(`/api/library/${id}`, { method: "DELETE" });
      if (res.ok) {
        router.push("/library");
        router.refresh();
      } else {
        const e = await res.json();
        alert(e.detail || "Failed");
      }
    } catch {
      alert("Something went wrong");
    } finally {
      setIsDeleting(false);
      setShowDeleteModal(false);
    }
  };

  const handleAddChapter = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsUploading(true);
    try {
      let res;
      if (addMode === "text") {
        res = await clientFetch(`/api/library/${id}`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ story: storyText }),
        });
      } else {
        const file = fileInputRef.current?.files?.[0];
        if (!file) return;
        const formData = new FormData();
        formData.append("file", file);
        res = await clientFetch(`/api/library/${id}`, {
          method: "POST",
          body: formData,
        });
      }
      if (res?.ok) setShowSuccessModal(true);
      else {
        const err = await res?.json();
        alert(err?.detail || "Upload failed");
      }
    } catch {
      alert("Something went wrong");
    } finally {
      setIsUploading(false);
      setShowAddModal(false);
    }
  };

  const handleUpdateNovel = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSaving(true);
    try {
      const formData = new FormData();
      if (editTitle) formData.append("title", editTitle);
      const file = editFileRef.current?.files?.[0];
      if (file) formData.append("cover", file);
      const res = await clientFetch(`/api/library/${id}`, {
        method: "PUT",
        body: formData,
      });
      if (!res.ok) throw new Error("");
      const updated = await res.json();
      setNovel((prev) =>
        prev
          ? {
              ...prev,
              title: updated.title || prev.title,
              cover: updated.cover || prev.cover,
            }
          : prev,
      );
      setShowEditModal(false);
    } catch {
      alert("Failed to update novel");
    } finally {
      setIsSaving(false);
    }
  };

  const getCoverUrl = (cover: string | null) => {
    if (!cover) return "/default-avatar.jpg";
    if (cover.startsWith("http")) return cover;
    return `${process.env.NEXT_PUBLIC_API_BASE_URL}${cover}`;
  };

  if (!novel)
    return (
      <div className={styles.loadingState}>
        <div className={styles.loadingBar}>
          <div className={styles.loadingFill} />
        </div>
        <span>Loading Novel…</span>
      </div>
    );

  const allSelected =
    selectedChapters.length === novel.chapters.length &&
    novel.chapters.length > 0;

  return (
    <div className={styles.container}>
      {/* ── HEADER ── */}
      <header className={styles.header}>
        <div className={styles.headerLeft}>
          <button
            className={styles.backBtn}
            onClick={() => router.push("/library")}
          >
            <ChevronLeft size={18} />
          </button>
          <div>
            <h1 className={styles.pageTitle}>{novel.title}</h1>
            <p className={styles.pageMeta}>{novel.chapters.length} chapters</p>
          </div>
        </div>
        <div className={styles.headerActions}>
          <button
            className={styles.iconBtn}
            title="Add Chapter"
            onClick={() => setShowAddModal(true)}
          >
            <Plus size={16} />
          </button>
          <button
            className={styles.iconBtn}
            title="Edit Novel"
            onClick={() => {
              setEditTitle(novel.title);
              setShowEditModal(true);
            }}
          >
            <Pencil size={16} />
          </button>
          <button
            className={styles.iconBtnDanger}
            title="Delete Novel"
            onClick={() => setShowDeleteModal(true)}
          >
            <Trash2 size={16} />
          </button>
        </div>
      </header>

      {/* ── MAIN LAYOUT ── */}
      <div className={styles.mainLayout}>
        {/* Chapter list */}
        <div className={styles.chapterSection}>
          <div className={styles.chapterHeader}>
            <span className={styles.chapterHeaderLabel}>Chapters</span>
            {novel.chapters.length > 0 && (
              <button className={styles.selectAllBtn} onClick={handleSelectAll}>
                {allSelected ? "Deselect all" : "Select all"}
              </button>
            )}
          </div>

          {novel.chapters.length === 0 ? (
            <div className={styles.emptyChapters}>
              <p>No chapters yet. Add your first chapter.</p>
            </div>
          ) : (
            <div className={styles.chapterList}>
              {novel.chapters.map((chap) => (
                <div
                  key={chap.id}
                  className={`${styles.chapterRow} ${selectedChapters.includes(chap.id) ? styles.chapterSelected : ""}`}
                  onClick={() =>
                    router.push(`/library/${id}/chapters/${chap.id}`)
                  }
                >
                  <input
                    type="checkbox"
                    className={styles.checkbox}
                    checked={selectedChapters.includes(chap.id)}
                    onChange={(e) => {
                      e.stopPropagation();
                      toggleChapter(chap.id);
                    }}
                    onClick={(e) => e.stopPropagation()}
                  />
                  <span className={styles.chapterOrder}>#{chap.order}</span>
                  <span className={styles.chapterTitle}>{chap.title}</span>
                  {chap.is_analyzed && (
                    <CheckCircle2 size={16} className={styles.doneIcon} />
                  )}
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Sidebar */}
        <aside className={styles.sidebar}>
          {/* Characters */}
          <div className={styles.sideCard}>
            <div className={styles.sideCardHead}>
              <Users size={14} />
              <span>Characters</span>
              <span className={styles.sideCardCount}>
                {novel.characters.length}
              </span>
            </div>
            {novel.characters.length > 0 ? (
              <div className={styles.charGrid}>
                {novel.characters.slice(0, 4).map((char, i) => (
                  <div key={i} className={styles.charCard}>
                    <div className={styles.charImgWrap}>
                      <Image
                        src={getCoverUrl(char.master_image_path)}
                        alt={char.name}
                        fill
                        className={styles.charImg}
                        unoptimized
                        loading="eager"
                      />
                    </div>
                    <p className={styles.charName}>{char.name}</p>
                  </div>
                ))}
              </div>
            ) : (
              <p className={styles.noCharText}>No characters analyzed yet.</p>
            )}
            <button
              className={styles.outlineBtn}
              onClick={() => router.push(`/library/${id}/characters`)}
            >
              View All Characters
            </button>
          </div>

          {/* Analyze CTA */}
          <div className={styles.ctaCard}>
            <div className={styles.ctaInfo}>
              <Zap size={16} className={styles.ctaIcon} />
              <div>
                <p className={styles.ctaTitle}>Ready to analyze</p>
                <p className={styles.ctaDesc}>
                  {selectedChapters.length > 0
                    ? `${selectedChapters.length} chapter${selectedChapters.length > 1 ? "s" : ""} selected`
                    : "Select chapters to begin"}
                </p>
              </div>
            </div>
            <button
              className={styles.analyzeBtn}
              disabled={selectedChapters.length === 0 || isCreating}
              onClick={handleAnalyze}
            >
              {isCreating ? "Creating..." : "Analyze"}
            </button>

            {/* <button
              className={styles.outlineBtn}
              style={{
                width: "100%",
                borderColor: "#6366f1",
                color: "#6366f1",
                display: "flex",
                flexDirection: "column",
                height: "auto",
                padding: "10px",
              }}
              disabled={selectedChapters.length === 0 || isFixing}
              onClick={handleFixText}
            >
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: "8px",
                  fontWeight: "bold",
                }}
              >
                <Pencil size={14} />
                {isFixing ? "Fixing..." : "AI Fix Text (Beta)"}
              </div>

              {selectedChapters.length > 0 && (
                <span
                  style={{ fontSize: "11px", opacity: 0.8, marginTop: "2px" }}
                >
                  Requires {totalFixCost} Credits
                </span>
              )}
            </button> */}
          </div>
        </aside>
      </div>

      {/* ── ADD CHAPTER MODAL ── */}
      {showAddModal && (
        <div
          className={styles.overlay}
          onClick={() => {
            setShowAddModal(false);
            setAddMode(null);
          }}
        >
          <div className={styles.modal} onClick={(e) => e.stopPropagation()}>
            <div className={styles.modalHeader}>
              <h2>
                {addMode
                  ? addMode === "text"
                    ? "Paste Text"
                    : "Upload File"
                  : "Add Chapter"}
              </h2>
              <button
                className={styles.closeBtn}
                onClick={() => {
                  setShowAddModal(false);
                  setAddMode(null);
                }}
              >
                <X size={18} />
              </button>
            </div>

            {!addMode ? (
              <div className={styles.modeGrid}>
                <button
                  className={styles.modeBtn}
                  onClick={() => setAddMode("text")}
                >
                  <FileText size={28} strokeWidth={1.5} />
                  <span>Paste Text</span>
                </button>
                <button
                  className={styles.modeBtn}
                  onClick={() => setAddMode("file")}
                >
                  <UploadCloud size={28} strokeWidth={1.5} />
                  <span>Upload File</span>
                </button>
              </div>
            ) : (
              <form onSubmit={handleAddChapter}>
                {addMode === "text" ? (
                  <textarea
                    className={styles.textarea}
                    placeholder="Paste your story content here..."
                    value={storyText}
                    onChange={(e) => setStoryText(e.target.value)}
                    required
                  />
                ) : (
                  <div className={styles.fileZone}>
                    <UploadCloud
                      size={32}
                      strokeWidth={1.2}
                      className={styles.fileZoneIcon}
                    />
                    <p>Supports .txt and .pdf</p>
                    <input
                      type="file"
                      ref={fileInputRef}
                      accept=".txt,.pdf"
                      required
                      className={styles.fileInput}
                    />
                  </div>
                )}
                <div className={styles.modalFooter}>
                  <button
                    type="button"
                    className={styles.cancelBtn}
                    onClick={() => setAddMode(null)}
                  >
                    Back
                  </button>
                  <button
                    type="submit"
                    className={styles.createBtn}
                    disabled={isUploading}
                  >
                    {isUploading ? "Processing..." : "Submit"}
                  </button>
                </div>
              </form>
            )}
          </div>
        </div>
      )}

      {/* ── EDIT MODAL ── */}
      {showEditModal && (
        <div className={styles.overlay} onClick={() => setShowEditModal(false)}>
          <div className={styles.modal} onClick={(e) => e.stopPropagation()}>
            <div className={styles.modalHeader}>
              <h2>Edit Novel</h2>
              <button
                className={styles.closeBtn}
                onClick={() => setShowEditModal(false)}
              >
                <X size={18} />
              </button>
            </div>
            <form onSubmit={handleUpdateNovel}>
              <div className={styles.fieldGroup}>
                <label className={styles.fieldLabel}>Title</label>
                <input
                  type="text"
                  value={editTitle}
                  onChange={(e) => setEditTitle(e.target.value)}
                  className={styles.input}
                  required
                />
              </div>
              <div className={styles.fieldGroup}>
                <label className={styles.fieldLabel}>Change Cover</label>
                <input
                  type="file"
                  ref={editFileRef}
                  accept="image/*"
                  className={styles.fileInput}
                />
                <p className={styles.helperText}>
                  Leave empty to keep current cover
                </p>
              </div>
              <div className={styles.modalFooter}>
                <button
                  type="button"
                  className={styles.cancelBtn}
                  onClick={() => setShowEditModal(false)}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className={styles.createBtn}
                  disabled={isSaving}
                >
                  {isSaving ? "Saving..." : "Save"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ── MODALS ── */}
      {showDeleteModal && (
        <SharePopUpDelete
          isOpen={showDeleteModal}
          onClose={() => setShowDeleteModal(false)}
          onConfirm={handleDelete}
          isLoading={isDeleting}
          title="Delete Novel?"
          description={
            <p>
              Delete <strong>"{novel.title}"</strong>? All chapters will be
              lost.
            </p>
          }
        />
      )}
      <SharePopUpAction
        isOpen={showSuccessModal}
        type="success"
        title="Upload Success!"
        primaryText="Done"
        onPrimary={handleSuccessClose}
        onClose={() => setShowSuccessModal(false)}
      />
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

      <SharePopUpAction
        isOpen={showFixSuccessModal}
        type="success"
        title="Fixing Started!"
        description="AI is correcting your text in the background. You will be notified when finished."
        primaryText="OK"
        onPrimary={() => setShowFixSuccessModal(false)}
        onClose={() => setShowFixSuccessModal(false)}
      />
    </div>
  );
}
