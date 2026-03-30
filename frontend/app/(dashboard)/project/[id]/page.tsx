"use client";

import { useParams, useRouter } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useState, useRef, useEffect } from "react";
import {
  ChevronLeft,
  ImageIcon,
  Play,
  Pause,
  Loader2,
  Check,
  Volume2,
  Users,
  Film,
  AlignLeft,
} from "lucide-react";
import { fetchSessionData } from "@/app/services/project-data";
import type { SceneEntry } from "@/app/services/project-data";
import styles from "./page.module.css";

// ─── API ─────────────────────────────────────────────────

async function patchSentence(
  sessionId: string,
  sentenceId: number,
  payload: { sentence: string },
) {
  const res = await fetch(`/api/project/${sessionId}/sentence/${sentenceId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error("Failed to update sentence");
  return res.json();
}

// ─── Editable Sentence ───────────────────────────────────

function EditableSentence({
  value,
  onSave,
  saving,
  saved,
}: {
  value: string;
  onSave: (val: string) => void;
  saving: boolean;
  saved: boolean;
}) {
  const ref = useRef<HTMLDivElement>(null);
  const [isDirty, setIsDirty] = useState(false);

  useEffect(() => {
    if (ref.current && ref.current.innerText !== value) {
      ref.current.innerText = value;
      setIsDirty(false);
    }
  }, [value]);

  return (
    <div className={styles.editableWrap}>
      <div
        ref={ref}
        contentEditable
        suppressContentEditableWarning
        className={styles.editableField}
        onInput={() => {
          const val = ref.current?.innerText.trim() ?? "";
          setIsDirty(val !== value);
        }}
      />
      <div className={styles.editableActions}>
        {saving ? (
          <Loader2 size={11} className={styles.spinner} />
        ) : saved ? (
          <Check size={11} className={styles.savedIcon} />
        ) : isDirty ? (
          <button
            className={styles.commitBtn}
            onMouseDown={(e) => {
              e.preventDefault();
              const val = ref.current?.innerText.trim() ?? "";
              onSave(val);
              setIsDirty(false);
            }}
          >
            Save
          </button>
        ) : null}
      </div>
    </div>
  );
}

// ─── Scene Card ──────────────────────────────────────────

function SceneCard({
  scene,
  isGenerated,
  playingVoice,
  savedId,
  onVoiceToggle,
  onSave,
  mutation,
}: {
  scene: SceneEntry;
  isGenerated: boolean;
  playingVoice: number | null;
  savedId: number | null;
  onVoiceToggle: (id: number) => void;
  onSave: (sentenceId: number, value: string) => void;
  mutation: any;
}) {
  return (
    <article className={styles.sceneCard}>
      {/* ── SCENE IMAGE ── */}
      <div className={styles.sceneImageWrap}>
        {isGenerated && scene.image ? (
          <>
            <img src={scene.image} alt="" className={styles.sceneImg} />
            <div className={styles.sceneImgOverlay} />
          </>
        ) : (
          <div className={styles.sceneImgPlaceholder}>
            <Film size={32} strokeWidth={1} />
            <span>No Image</span>
          </div>
        )}

        {/* Badge */}
        <div className={styles.sceneBadge}>
          <span className={styles.sceneBadgeChapter}>
            Ch{scene.chapter_order}
          </span>
          <span className={styles.sceneBadgeDivider}>·</span>
          <span>Scene {scene.scene_index}</span>
        </div>

        {/* Description overlay */}
        {scene.description && (
          <div className={styles.sceneDescOverlay}>
            <p className={styles.sceneDescText}>{scene.description}</p>
          </div>
        )}
      </div>

      {/* ── CHARACTERS ── */}
      {scene.characters.length > 0 && (
        <div className={styles.section}>
          <div className={styles.sectionLabel}>
            <Users size={12} />
            <span>Characters</span>
          </div>
          <div className={styles.characterRow}>
            {scene.characters.map((c) => (
              <div key={c.id} className={styles.characterCard}>
                <div className={styles.characterImgWrap}>
                  {c.image ? (
                    <img
                      src={c.image}
                      alt={c.name}
                      className={styles.characterImg}
                    />
                  ) : (
                    <div className={styles.characterImgFallback}>
                      <span>{c.name.charAt(0).toUpperCase()}</span>
                    </div>
                  )}
                </div>
                <div className={styles.characterInfo}>
                  <span className={styles.characterName}>{c.name}</span>
                  {c.expression && (
                    <span className={styles.characterExpression}>
                      {c.expression}
                    </span>
                  )}
                  {c.action && (
                    <span className={styles.characterAction}>{c.action}</span>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ── SENTENCES ── */}
      {scene.sentences.length > 0 && (
        <div className={styles.section}>
          <div className={styles.sectionLabel}>
            <AlignLeft size={12} />
            <span>Dialogue · {scene.sentences.length} lines</span>
          </div>
          <div className={styles.sentenceList}>
            {scene.sentences.map((sent, idx) => (
              <div key={sent.id} className={styles.sentenceRow}>
                <span className={styles.sentenceIndex}>
                  {String(idx + 1).padStart(2, "0")}
                </span>

                <div className={styles.sentenceMain}>
                  <EditableSentence
                    value={sent.sentence}
                    saving={
                      mutation.isPending &&
                      mutation.variables?.sentenceId === sent.id
                    }
                    saved={savedId === sent.id}
                    onSave={(val) => onSave(sent.id, val)}
                  />
                </div>

                {isGenerated && sent.voice && (
                  <div className={styles.voiceControl}>
                    <audio id={`audio-${sent.id}`} src={sent.voice} />
                    <button
                      className={`${styles.voiceBtn} ${playingVoice === sent.id ? styles.voiceBtnActive : ""}`}
                      onClick={() => onVoiceToggle(sent.id)}
                      title="Play voice"
                    >
                      {playingVoice === sent.id ? (
                        <Pause size={12} />
                      ) : (
                        <Volume2 size={12} />
                      )}
                    </button>
                    {playingVoice === sent.id && (
                      <div className={styles.voiceWave}>
                        {[...Array(4)].map((_, i) => (
                          <span
                            key={i}
                            className={styles.voiceBar}
                            style={{ animationDelay: `${i * 0.12}s` }}
                          />
                        ))}
                      </div>
                    )}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </article>
  );
}

// ─── Page ────────────────────────────────────────────────

export default function ProjectDetailPage() {
  const { id } = useParams() as { id: string };
  const router = useRouter();
  const queryClient = useQueryClient();

  const [playingVoice, setPlayingVoice] = useState<number | null>(null);
  const [savedId, setSavedId] = useState<number | null>(null);

  const { data, isLoading } = useQuery({
    queryKey: ["project-data", id],
    queryFn: () => fetchSessionData(id),
  });

  const mutation = useMutation({
    mutationFn: ({
      sentenceId,
      value,
    }: {
      sentenceId: number;
      value: string;
    }) => patchSentence(id, sentenceId, { sentence: value }),
    onSuccess: (_, vars) => {
      setSavedId(vars.sentenceId);
      queryClient.setQueryData(["project-data", id], (old: any) => {
        if (!old) return old;
        return {
          ...old,
          scenes: old.scenes.map((scene: SceneEntry) => ({
            ...scene,
            sentences: scene.sentences.map((s) =>
              s.id === vars.sentenceId ? { ...s, sentence: vars.value } : s,
            ),
          })),
        };
      });
      setTimeout(() => setSavedId(null), 1500);
    },
  });

  const handleVoiceToggle = (sentId: number) => {
    const audio = document.getElementById(
      `audio-${sentId}`,
    ) as HTMLAudioElement;
    if (playingVoice === sentId) {
      setPlayingVoice(null);
      audio?.pause();
    } else {
      if (playingVoice) {
        (
          document.getElementById(`audio-${playingVoice}`) as HTMLAudioElement
        )?.pause();
      }
      setPlayingVoice(sentId);
      audio?.play();
      audio?.addEventListener("ended", () => setPlayingVoice(null), {
        once: true,
      });
    }
  };

  if (isLoading || !data) {
    return (
      <div className={styles.loadingState}>
        <div className={styles.loadingRing} />
        <span>Loading project…</span>
      </div>
    );
  }

  const totalCharacters = [
    ...new Map(
      data.scenes.flatMap((s) => s.characters).map((c) => [c.id, c]),
    ).values(),
  ].length;

  const totalSentences = data.scenes.reduce(
    (acc, s) => acc + s.sentences.length,
    0,
  );
  const isGenerated = data.is_generation_done;

  return (
    <div className={styles.container}>
      {/* ── HEADER ── */}
      <header className={styles.header}>
        <button onClick={() => router.back()} className={styles.backBtn}>
          <ChevronLeft size={18} />
        </button>
        <div className={styles.headerText}>
          <h1 className={styles.headerTitle}>{data.session_name}</h1>
          <div className={styles.headerMeta}>
            <span className={styles.stylePill}>{data.style}</span>
            {isGenerated && (
              <span className={styles.generatedPill}>Generated</span>
            )}
          </div>
        </div>
      </header>

      {/* ── STATS ── */}
      <div className={styles.statsRow}>
        {[
          {
            label: "Scenes",
            value: data.scenes.length,
            icon: <Film size={14} />,
          },
          {
            label: "Characters",
            value: totalCharacters,
            icon: <Users size={14} />,
          },
          {
            label: "Lines",
            value: totalSentences,
            icon: <AlignLeft size={14} />,
          },
        ].map((s) => (
          <div key={s.label} className={styles.statChip}>
            <span className={styles.statIcon}>{s.icon}</span>
            <span className={styles.statValue}>{s.value}</span>
            <span className={styles.statLabel}>{s.label}</span>
          </div>
        ))}
      </div>

      {/* ── SCENE LIST ── */}
      <div className={styles.sceneList}>
        {data.scenes.map((scene: SceneEntry, i: number) => (
          <div
            key={scene.id}
            className={styles.sceneWrapper}
            style={{ animationDelay: `${i * 0.05}s` }}
          >
            <SceneCard
              scene={scene}
              isGenerated={isGenerated}
              playingVoice={playingVoice}
              savedId={savedId}
              onVoiceToggle={handleVoiceToggle}
              onSave={(sentenceId, value) =>
                mutation.mutate({ sentenceId, value })
              }
              mutation={mutation}
            />
          </div>
        ))}
      </div>
    </div>
  );
}
