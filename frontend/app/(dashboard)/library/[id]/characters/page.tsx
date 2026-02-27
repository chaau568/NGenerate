"use client";

import { useEffect, useState, use } from "react";
import { clientFetch } from "@/lib/client-fetch";
import { ChevronLeft } from "lucide-react";
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
  master_voice_path: string | null;
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

  useEffect(() => {
    const fetchChars = async () => {
      try {
        const res = await clientFetch(`/api/library/${id}/characters`);
        if (res.ok) {
          const data = await res.json();
          setCharacters(data);
        }
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    };
    fetchChars();
  }, [id]);

  const getImageUrl = (path: string | null) => {
    if (!path) return "/default-avatar.jpg";
    if (path.startsWith("http")) return path;
    return `${process.env.NEXT_PUBLIC_API_BASE_URL}${path}`;
  };

  const getVoiceUrl = (path: string | null) => {
    if (!path) return undefined;
    const cleanPath = decodeURIComponent(path);
    if (cleanPath.startsWith("http")) return cleanPath;
    return `${process.env.NEXT_PUBLIC_API_BASE_URL}${cleanPath}`;
  };

  if (loading)
    return <div className={styles.loading}>Loading Characters...</div>;

  return (
    <div className={styles.container}>
      <header className={styles.header}>
        <div className={styles.headerLeft}>
          <button onClick={() => router.back()} className={styles.backBtn}>
            <ChevronLeft size={22} />
          </button>
          <h1>View Chapters</h1>
        </div>
      </header>

      <div className={styles.charGrid}>
        {characters.length > 0 ? (
          characters.map((char) => (
            <div key={char.id} className={styles.charCard}>
              <div className={styles.imageSection}>
                <Image
                  src={getImageUrl(char.master_image_path)}
                  alt={char.name}
                  fill
                  className={styles.charImg}
                  unoptimized
                  loading="eager"
                  priority
                />
              </div>
              <div className={styles.infoSection}>
                <h2>{char.name}</h2>
                <div className={styles.tags}>
                  {char.sex && <span className={styles.tag}>{char.sex}</span>}
                  {char.age && (
                    <span className={styles.tag}>Age: {char.age}</span>
                  )}
                  {char.race && <span className={styles.tag}>{char.race}</span>}
                </div>
                <div className={styles.details}>
                  <p>
                    <strong>Personality:</strong>{" "}
                    {char.base_personality || "N/A"}
                  </p>
                  <p>
                    <strong>Appearance:</strong> {char.appearance || "N/A"}
                  </p>
                </div>
                {char.master_voice_path && (
                  <div className={styles.audioWrapper}>
                    <audio
                      controls
                      src={getVoiceUrl(char.master_voice_path)}
                      className={styles.audioPlayer}
                    />
                  </div>
                )}
              </div>
            </div>
          ))
        ) : (
          <p className={styles.empty}>No characters found in this novel.</p>
        )}
      </div>
    </div>
  );
}
