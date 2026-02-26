"use client";

import { clientFetch } from "@/lib/client-fetch";
import { useEffect, useState } from "react";
import Link from "next/link";
import { Plus } from "lucide-react";
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

  const handleImageChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      setSelectedFile(file);
      setPreviewUrl(URL.createObjectURL(file));
    }
  };

  useEffect(() => {
    let timer: NodeJS.Timeout;

    if (showSuccessModal) {
      timer = setTimeout(() => {
        handleSuccessClose();
      }, 5000);
    }

    return () => clearTimeout(timer);
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
      if (selectedFile) {
        formData.append("cover", selectedFile);
      }

      const res = await clientFetch("/api/library/create", {
        method: "POST",
        body: formData,
      });

      if (res.ok) {
        const result = await res.json();
        console.log("Created successfully:", result);
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
      console.error("Client Fetch Error:", error);
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
    return <div className={styles.statusText}>Loading Library...</div>;

  return (
    <div className={styles.container}>
      <header className={styles.header}>
        <div className={styles.titleGroup}>
          <h1>My Novel Library</h1>
          <span className={styles.badge}>{data?.total_novels || 0} novels</span>
        </div>
        <button className={styles.addBtn} onClick={() => setIsModalOpen(true)}>
          <Plus size={32} strokeWidth={2.5} />
          <span>Add New Novel</span>
        </button>
      </header>

      {/* Grid Section */}
      <div className={styles.grid}>
        {data?.chapters.map((novel) => (
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
              </div>
              <div className={styles.cardInfo}>
                <h3 className={styles.novelTitle}>{novel.title}</h3>
                <p className={styles.novelChapters}>
                  {novel.analyzed_chapters}/{novel.total_chapters} Chapters
                </p>
              </div>
            </div>
          </Link>
        ))}
      </div>

      {/* CREATE MODAL */}
      {isModalOpen && (
        <div className={styles.modalOverlay}>
          <div className={styles.modalContent}>
            <h2>Create New Novel</h2>
            <form onSubmit={handleCreateNovel}>
              {/* เพิ่มส่วน Upload Cover ตรงนี้ */}
              <div className={styles.uploadSection}>
                <label className={styles.uploadBox}>
                  {previewUrl ? (
                    <Image
                      src={previewUrl}
                      alt="Preview"
                      fill
                      className={styles.previewImg}
                      unoptimized
                      loading="eager"
                      priority
                    />
                  ) : (
                    <div className={styles.uploadPlaceholder}>
                      <span className={styles.plusIconLarge}>+</span>
                      <p>Upload Cover</p>
                    </div>
                  )}
                  <input
                    type="file"
                    accept="image/*"
                    onChange={handleImageChange}
                    hidden
                  />
                </label>
              </div>

              <label className={styles.modalLabel}>Novel Title</label>
              <input
                autoFocus
                className={styles.modalInput}
                type="text"
                value={newTitle}
                onChange={(e) => setNewTitle(e.target.value)}
                placeholder="Enter novel title..."
                required
              />

              <div className={styles.modalActions}>
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
                  className={styles.confirmBtn}
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
        title="Upload Success!"
      />
    </div>
  );
}
