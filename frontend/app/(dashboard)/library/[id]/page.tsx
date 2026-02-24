"use client";

import { clientFetch } from "@/lib/client-fetch";
import { useEffect, useState, use, useRef } from "react";
import { useRouter, useParams } from "next/navigation";
import {
  Plus,
  Trash2,
  CheckCircle2,
  AlertTriangle,
  FileText,
  UploadCloud,
} from "lucide-react";
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

  useEffect(() => {
    if (!id) return;

    const loadNovel = async () => {
      const res = await clientFetch(`/api/library/${id}`);

      if (!res.ok) {
        if (res.status === 401) {
          window.location.href = "/login";
          return;
        }
        throw new Error("Failed to fetch novel");
      }

      const data = await res.json();

      setNovel({
        ...data,
        chapters: data.chapters ?? [],
        characters: data.characters ?? [],
      });
    };

    loadNovel();
  }, [id]);

  const handleDelete = async () => {
    setIsDeleting(true);
    try {
      const res = await clientFetch(`/api/library/${id}`, {
        method: "DELETE",
      });

      if (res.ok) {
        router.push("/library");
        router.refresh();
      } else {
        const errorData = await res.json();
        alert(errorData.detail || "Failed to delete novel");
      }
    } catch (error) {
      console.error("Delete error:", error);
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

      if (res.ok) {
        alert("Success!");
        window.location.reload();
      } else {
        const err = await res.json();
        alert(err.detail || "Upload failed");
      }
    } catch (err) {
      alert("Something went wrong");
    } finally {
      setIsUploading(false);
      setShowAddModal(false);
    }
  };

  if (!novel) return <div className={styles.loading}>Loading...</div>;

  const toggleChapter = (chapterId: number) => {
    setSelectedChapters((prev) =>
      prev.includes(chapterId)
        ? prev.filter((i) => i !== chapterId)
        : [...prev, chapterId],
    );
  };

  const getCoverUrl = (cover: string | null) => {
    if (!cover) return "/default-avatar.jpg";
    if (cover.startsWith("http")) return cover;
    return `${process.env.NEXT_PUBLIC_API_BASE_URL}${cover}`;
  };

  const goToViewCharacters = () => {
    router.push(`/library/${id}/characters`);
  };

  return (
    <div className={styles.container}>
      <header className={styles.header}>
        <h1>{novel.title}</h1>
        <div className={styles.actionButtons}>
          <button
            className={styles.addBtn}
            onClick={() => setShowAddModal(true)}
          >
            <Plus size={32} strokeWidth={2.5} />
            <span>Add New Chapter</span>
          </button>

          <button
            className={styles.deleteBtn}
            aria-label="Delete"
            onClick={() => setShowDeleteModal(true)}
          >
            <Trash2 size={32} strokeWidth={2.5} />
          </button>
        </div>
      </header>

      <div className={styles.mainLayout}>
        {/* Left: Chapter List */}
        <div className={styles.chapterSection}>
          {novel.chapters.map((chap) => (
            <div key={chap.id} className={styles.chapterRow}>
              {/* 1. ปุ่มติ๊กเลือก (ซ้ายสุด) */}
              <input
                type="checkbox"
                className={styles.checkbox} // เพิ่ม class เพื่อแต่งหน้าตา
                checked={selectedChapters.includes(chap.id)}
                onChange={() => toggleChapter(chap.id)}
              />

              {/* 2. ชื่อตอน (ตรงกลาง) */}
              <span className={styles.chapterTitle}>{chap.title}</span>

              {/* 3. ติ๊กถูกสีเขียว (ขวาสุด - แสดงเมื่อวิเคราะห์แล้ว) */}
              <div className={styles.statusWrapper}>
                {chap.is_analyzed && (
                  <CheckCircle2
                    size={24}
                    strokeWidth={2.8}
                    className={styles.doneIcon}
                  />
                )}
              </div>
            </div>
          ))}
        </div>

        {/* Right: Character Sidebar */}
        <aside className={styles.characterSection}>
          <div className={styles.charGrid}>
            {novel.characters && novel.characters.length > 0 ? (
              novel.characters.slice(0, 4).map((char, index) => (
                <div key={index} className={styles.charCard}>
                  <div className={styles.charImgWrapper}>
                    <Image
                      src={getCoverUrl(char.master_image_path)}
                      alt={char.name}
                      fill
                      className={styles.avatarImg}
                      unoptimized
                      loading="eager"
                      priority
                    />
                  </div>
                  <p className={styles.charName}>{char.name}</p>
                </div>
              ))
            ) : (
              <p className={styles.noCharText}>No characters analyzed yet.</p>
            )}
          </div>

          <button className={styles.viewCharBtn} onClick={goToViewCharacters}>
            View All Characters
          </button>

          <button
            className={styles.analyzeBtn}
            disabled={selectedChapters.length === 0}
          >
            Analyze ({selectedChapters.length} selected)
          </button>
        </aside>
      </div>

      {showDeleteModal && (
        <div className={styles.modalOverlay}>
          <div className={styles.modalContent}>
            <div className={styles.modalIcon}>
              <AlertTriangle size={48} color="#ef4444" />
            </div>
            <h3>Delete Novel?</h3>
            <p>
              Are you sure you want to delete <strong>"{novel.title}"</strong>?
              This action cannot be undone and all chapters will be lost.
            </p>
            <div className={styles.modalActions}>
              <button
                className={styles.cancelBtn}
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

      {showAddModal && (
        <div className={styles.modalOverlay}>
          <div className={`${styles.modalContent} ${styles.addModal}`}>
            <h3>Add New Chapter</h3>

            {!addMode ? (
              <div className={styles.modeSelection}>
                <button
                  onClick={() => setAddMode("text")}
                  className={styles.modeBtn}
                >
                  <FileText size={40} />
                  <span>Upload by Text</span>
                </button>
                <button
                  onClick={() => setAddMode("file")}
                  className={styles.modeBtn}
                >
                  <UploadCloud size={40} />
                  <span>Upload by File</span>
                </button>
              </div>
            ) : (
              <form onSubmit={handleAddChapter}>
                {addMode === "text" ? (
                  <textarea
                    className={styles.textArea}
                    placeholder="Paste your story content here..."
                    value={storyText}
                    onChange={(e) => setStoryText(e.target.value)}
                    required
                  />
                ) : (
                  <div className={styles.fileUploadArea}>
                    <input
                      type="file"
                      ref={fileInputRef}
                      accept=".txt,.pdf"
                      required
                      className={styles.fileInput}
                    />
                    <p>Support .txt and .pdf only</p>
                  </div>
                )}

                <div className={styles.modalActions}>
                  <button
                    type="button"
                    className={styles.cancelBtn}
                    onClick={() => {
                      setAddMode(null);
                      setShowAddModal(false);
                    }}
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    className={styles.confirmAddBtn}
                    disabled={isUploading}
                  >
                    {isUploading ? "Processing..." : "Submit"}
                  </button>
                </div>
              </form>
            )}
            {!addMode && (
              <button
                type="button"
                className={styles.cancelBtn}
                onClick={() => {
                  setShowAddModal(false);
                }}
              >
                Cancel
              </button>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
