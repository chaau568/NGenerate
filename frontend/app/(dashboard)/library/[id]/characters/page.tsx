"use client";

import { useEffect, useState, use } from "react";
import { clientFetch } from "@/lib/client-fetch";
import { ChevronLeft, User } from "lucide-react";
import { useRouter } from "next/navigation";
import Image from "next/image";
import styles from "./page.module.css";

interface CharacterProfile {
  id: number;
  name: string;
  appearance: string;
  outfit: string;
  sex: string;
  age: string;
  race: string;
  base_personality: string;
  master_image_path: string | null;
}

export default function CharacterListPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const router = useRouter();
  const [characters, setCharacters] = useState<CharacterProfile[]>([]);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState<number | null>(null);

  useEffect(() => {
    clientFetch(`/api/library/${id}/characters`)
      .then(async (res) => {
        if (res.ok) setCharacters(await res.json());
      })
      .finally(() => setLoading(false));
  }, [id]);

  const getImageUrl = (path: string | null) => {
    if (!path) return "/default-avatar.jpg";
    if (path.startsWith("http")) return path;
    return `${process.env.NEXT_PUBLIC_API_BASE_URL}${path}`;
  };

  if (loading)
    return (
      <div className={styles.loadingState}>
        <div className={styles.loadingBar}>
          <div className={styles.loadingFill} />
        </div>
        <span>Loading Characters…</span>
      </div>
    );

  const active =
    selected !== null
      ? (characters.find((c) => c.id === selected) ?? null)
      : null;

  return (
    <div className={styles.container}>
      {/* ── HEADER ── */}
      <header className={styles.header}>
        <button onClick={() => router.back()} className={styles.backBtn}>
          <ChevronLeft size={18} />
        </button>
        <div>
          <h1 className={styles.pageTitle}>Characters</h1>
          <p className={styles.pageMeta}>{characters.length} profiles</p>
        </div>
      </header>

      {characters.length === 0 ? (
        <div className={styles.emptyState}>
          <User size={44} strokeWidth={1.2} className={styles.emptyIcon} />
          <p className={styles.emptyTitle}>No characters yet</p>
          <p className={styles.emptyDesc}>
            Analyze chapters to discover characters.
          </p>
        </div>
      ) : (
        <div className={styles.layout}>
          {/* List */}
          <div className={styles.charList}>
            {characters.map((char) => (
              <button
                key={char.id}
                className={`${styles.charRow} ${selected === char.id ? styles.charRowActive : ""}`}
                onClick={() =>
                  setSelected(selected === char.id ? null : char.id)
                }
              >
                <div className={styles.charRowAvatar}>
                  <Image
                    src={getImageUrl(char.master_image_path)}
                    alt={char.name}
                    fill
                    className={styles.avatarImg}
                    unoptimized
                  />
                </div>
                <div className={styles.charRowInfo}>
                  <p className={styles.charRowName}>{char.name}</p>
                  <p className={styles.charRowMeta}>
                    {[char.sex, char.age ? `Age ${char.age}` : null, char.race]
                      .filter(Boolean)
                      .join(" · ")}
                  </p>
                </div>
                {char.master_image_path &&
                  char.master_image_path !== "/default-avatar.jpg" && (
                    <span className={styles.hasImageDot} />
                  )}
              </button>
            ))}
          </div>

          {/* Detail panel */}
          <div
            className={`${styles.detailPanel} ${active ? styles.detailPanelVisible : ""}`}
          >
            {active ? (
              <>
                <div className={styles.detailImage}>
                  <Image
                    src={getImageUrl(active.master_image_path)}
                    alt={active.name}
                    fill
                    className={styles.detailImg}
                    unoptimized
                  />
                  <div className={styles.detailImageGrad} />
                  <h2 className={styles.detailName}>{active.name}</h2>
                </div>

                <div className={styles.detailBody}>
                  <div className={styles.tagRow}>
                    {active.sex && (
                      <span className={styles.tag}>{active.sex}</span>
                    )}
                    {active.age && (
                      <span className={styles.tag}>Age {active.age}</span>
                    )}
                    {active.race && (
                      <span className={styles.tag}>{active.race}</span>
                    )}
                  </div>

                  {active.base_personality && (
                    <div className={styles.detailSection}>
                      <p className={styles.detailLabel}>Personality</p>
                      <p className={styles.detailText}>
                        {active.base_personality}
                      </p>
                    </div>
                  )}
                  {active.appearance && (
                    <div className={styles.detailSection}>
                      <p className={styles.detailLabel}>Appearance</p>
                      <p className={styles.detailText}>{active.appearance}</p>
                    </div>
                  )}
                  {active.outfit && (
                    <div className={styles.detailSection}>
                      <p className={styles.detailLabel}>Outfit</p>
                      <p className={styles.detailText}>{active.outfit}</p>
                    </div>
                  )}
                </div>
              </>
            ) : (
              <div className={styles.detailEmpty}>
                <User size={32} strokeWidth={1.2} />
                <p>Select a character</p>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
