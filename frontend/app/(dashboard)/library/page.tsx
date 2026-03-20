"use client";

import { clientFetch } from "@/lib/client-fetch";
import { useEffect, useState } from "react";
import Link from "next/link";
import { Plus, BookOpen, X } from "lucide-react";
import SharePopUpSuccess from "@/components/SharePopUp_Success";
import styles from "./page.module.css";
import Image from "next/image";

interface Novel {
  id: number;
  title: string;
  cover: string | null;
  total_chapters: number;
  analyzed_chapters: number;
}

interface LibraryData {
  total_novels: number;
  chapters: Novel[];
}

export default function LibraryPage() {
  const [data, setData] = useState<LibraryData | null>(null);
  const [loading, setLoading] = useState(true);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [newTitle, setNewTitle] = useState("");
  const [isCreating, setIsCreating] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [showSuccessModal, setShowSuccessModal] = useState(false);

  const fetchLibrary = async () => {
    try {
      const res = await clientFetch("/api/library");
      const result = await res.json();
      if (!res.ok) throw new Error(result.detail || "Failed to fetch");
      setData(result);
    } catch (error) {
      console.error("Library Error:", error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchLibrary();
  }, []);

  useEffect(() => {
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setIsModalOpen(false);
    };
    window.addEventListener("keydown", handleKey);
    return () => window.removeEventListener("keydown", handleKey);
  }, []);

  const handleImageChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      setSelectedFile(file);
      setPreviewUrl(URL.createObjectURL(file));
    }
  };

  useEffect(() => {
    if (!showSuccessModal) return;
    const t = setTimeout(handleSuccessClose, 5000);
    return () => clearTimeout(t);
  }, [showSuccessModal]);

  const handleSuccessClose = () => {
    setShowSuccessModal(false);
    window.location.reload();
  };

  const handleCreateNovel = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (!newTitle.trim()) return;
    setIsCreating(true);
    try {
      const formData = new FormData();
      formData.append("title", newTitle);
      if (selectedFile) formData.append("cover", selectedFile);
      const res = await clientFetch("/api/library/create", {
        method: "POST",
        body: formData,
      });
      if (res.ok) {
        setNewTitle("");
        setSelectedFile(null);
        setPreviewUrl(null);
        setIsModalOpen(false);
        setShowSuccessModal(true);
      } else {
        const err = await res.json();
        alert(err.error || err.detail || "Create failed");
      }
    } catch (error) {
      console.error(error);
    } finally {
      setIsCreating(false);
    }
  };

  const getCoverUrl = (cover: string | null) => {
    if (!cover) return "/default-cover.jpg";
    if (cover.startsWith("http")) return cover;
    return `${process.env.NEXT_PUBLIC_API_BASE_URL}${cover}`;
  };

  if (loading)
    return (
      <div className={styles.loadingState}>
        <div className={styles.loadingBar}>
          <div className={styles.loadingFill} />
        </div>
        <span>Loading Library...</span>
      </div>
    );

  return (
    <div className={styles.container}>
      <header className={styles.header}>
        <div className={styles.titleGroup}>
          <h1 className={styles.pageTitle}>Library</h1>
          <span className={styles.badge}>{data?.total_novels || 0}</span>
        </div>
        <button className={styles.addBtn} onClick={() => setIsModalOpen(true)}>
          <Plus size={16} strokeWidth={2.5} />
          New Novel
        </button>
      </header>

      {!data?.chapters || data.chapters.length === 0 ? (
        <div className={styles.emptyState}>
          <BookOpen size={48} strokeWidth={1.2} className={styles.emptyIcon} />
          <p className={styles.emptyTitle}>No novels yet</p>
          <p className={styles.emptyDesc}>
            Create your first novel to get started.
          </p>
        </div>
      ) : (
        <div className={styles.grid}>
          {data.chapters.map((novel) => {
            const progress =
              novel.total_chapters > 0
                ? Math.round(
                    (novel.analyzed_chapters / novel.total_chapters) * 100,
                  )
                : 0;
            return (
              <Link
                href={`/library/${novel.id}`}
                key={novel.id}
                className={styles.cardLink}
              >
                <div className={styles.card}>
                  <div className={styles.coverWrapper}>
                    <Image
                      src={getCoverUrl(novel.cover)}
                      alt={novel.title}
                      fill
                      className={styles.coverImg}
                      unoptimized
                      loading="eager"
                      priority
                    />
                    {novel.analyzed_chapters > 0 && (
                      <div className={styles.progressPill}>
                        {novel.analyzed_chapters}/{novel.total_chapters}
                      </div>
                    )}
                  </div>
                  <div className={styles.cardInfo}>
                    <h3 className={styles.novelTitle}>{novel.title}</h3>
                    <p className={styles.novelMeta}>
                      {novel.total_chapters} chapters
                    </p>
                    {novel.total_chapters > 0 && (
                      <div className={styles.progressBar}>
                        <div
                          className={styles.progressFill}
                          style={{ width: `${progress}%` }}
                        />
                      </div>
                    )}
                  </div>
                </div>
              </Link>
            );
          })}
        </div>
      )}

      {/* CREATE MODAL */}
      {isModalOpen && (
        <div className={styles.overlay} onClick={() => setIsModalOpen(false)}>
          <div className={styles.modal} onClick={(e) => e.stopPropagation()}>
            <div className={styles.modalHeader}>
              <h2>New Novel</h2>
              <button
                className={styles.closeBtn}
                onClick={() => setIsModalOpen(false)}
              >
                <X size={18} />
              </button>
            </div>

            <form onSubmit={handleCreateNovel}>
              <div className={styles.uploadRow}>
                <label className={styles.uploadBox}>
                  {previewUrl ? (
                    <Image
                      src={previewUrl}
                      alt="Preview"
                      fill
                      className={styles.previewImg}
                      unoptimized
                      loading="eager"
                    />
                  ) : (
                    <div className={styles.uploadPlaceholder}>
                      <Plus size={24} strokeWidth={1.5} />
                      <span>Cover</span>
                    </div>
                  )}
                  <input
                    type="file"
                    accept="image/*"
                    onChange={handleImageChange}
                    hidden
                  />
                </label>

                <div className={styles.uploadRight}>
                  <label className={styles.fieldLabel}>Novel Title</label>
                  <input
                    autoFocus
                    className={styles.input}
                    type="text"
                    value={newTitle}
                    onChange={(e) => setNewTitle(e.target.value)}
                    placeholder="Enter title..."
                    required
                  />
                </div>
              </div>

              <div className={styles.modalFooter}>
                <button
                  type="button"
                  className={styles.cancelBtn}
                  onClick={() => {
                    setIsModalOpen(false);
                    setPreviewUrl(null);
                    setSelectedFile(null);
                  }}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className={styles.createBtn}
                  disabled={isCreating}
                >
                  {isCreating ? "Creating..." : "Create Novel"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      <SharePopUpSuccess
        isOpen={showSuccessModal}
        onClose={handleSuccessClose}
        title="Novel Created!"
      />
    </div>
  );
}
