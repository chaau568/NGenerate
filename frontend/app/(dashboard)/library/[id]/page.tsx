"use client";

import { clientFetch } from "@/lib/client-fetch";
import { useEffect, useState, use } from "react";
import { Plus, Trash2, CheckCircle2 } from "lucide-react";
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

export default function NovelDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const [novel, setNovel] = useState<NovelDetail | null>(null);
  const [selectedChapters, setSelectedChapters] = useState<number[]>([]);

  useEffect(() => {
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

  return (
    <div className={styles.container}>
      <header className={styles.header}>
        <h1>{novel.title}</h1>
        <div className={styles.actionButtons}>
          <button className={styles.addBtn}>
            <Plus size={32} strokeWidth={2.5} />
            <span>Add New Chapter</span>
          </button>

          <button className={styles.deleteBtn} aria-label="Delete">
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
                    />
                  </div>
                  <p className={styles.charName}>{char.name}</p>
                </div>
              ))
            ) : (
              <p className={styles.noCharText}>No characters analyzed yet.</p>
            )}
          </div>

          <button className={styles.viewCharBtn}>View All Characters</button>

          <button
            className={styles.analyzeBtn}
            disabled={selectedChapters.length === 0}
          >
            Analyze ({selectedChapters.length} selected)
          </button>
        </aside>
      </div>
    </div>
  );
}
