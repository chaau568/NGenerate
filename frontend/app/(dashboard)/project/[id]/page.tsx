"use client";

import { useParams, useRouter } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useState, useRef, useEffect, useCallback } from "react";
import {
  ChevronLeft,
  User,
  MessageSquare,
  Image,
  Play,
  Pause,
  ChevronDown,
  Loader2,
  Check,
} from "lucide-react";
import { createPortal } from "react-dom";
import { fetchSessionData } from "@/app/services/project-data";
import type {
  CharacterEntry,
  SentenceEntry,
  SceneEntry,
} from "@/app/services/project-data";
import styles from "./page.module.css";

// ─── types ────────────────────────────────────────────────────────────────────

type Tab = "characters" | "sentences" | "scenes";

interface SentenceEditState {
  sentence: string;
  tts_text: string;
  emotion: string;
}

// ─── API helpers ──────────────────────────────────────────────────────────────

async function fetchEmotionChoices(): Promise<EmotionOption[]> {
  const res = await fetch("/api/sessions/emotion-choices");
  if (!res.ok) throw new Error("Failed to fetch emotions");
  const data = await res.json();
  return (data.emotions as unknown[]).map((e) =>
    Array.isArray(e)
      ? { value: e[0] as string, label: e[1] as string }
      : { value: e as string, label: e as string },
  );
}

async function patchSentence(
  sessionId: string,
  sentenceId: number,
  payload: Partial<SentenceEditState>,
): Promise<SentenceEditState & { id: number }> {
  const res = await fetch(`/api/project/${sessionId}/sentence/${sentenceId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err?.error ?? "Failed to update sentence");
  }
  return res.json();
}

// ─── emotion dropdown ─────────────────────────────────────────────────────────

interface EmotionOption {
  value: string;
  label: string;
}

interface EmotionDropdownProps {
  value: string;
  options: EmotionOption[];
  onChange: (val: string) => void;
  saving?: boolean;
  saved?: boolean;
}

function EmotionDropdown({
  value,
  options,
  onChange,
  saving,
  saved,
}: EmotionDropdownProps) {
  const [open, setOpen] = useState(false);
  const triggerRef = useRef<HTMLButtonElement>(null);
  const menuRef = useRef<HTMLDivElement>(null);
  const [menuPos, setMenuPos] = useState({ top: 0, left: 0 });

  const currentLabel = options.find((o) => o.value === value)?.label ?? value;

  const openMenu = () => {
    if (triggerRef.current) {
      const rect = triggerRef.current.getBoundingClientRect();
      setMenuPos({
        top: rect.bottom + window.scrollY + 5,
        left: rect.left + window.scrollX,
      });
    }
    setOpen(true);
  };

  useEffect(() => {
    if (!open) return;
    const handler = (e: MouseEvent) => {
      if (
        menuRef.current &&
        !menuRef.current.contains(e.target as Node) &&
        triggerRef.current &&
        !triggerRef.current.contains(e.target as Node)
      )
        setOpen(false);
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [open]);

  return (
    <div className={styles.emotionDropdownWrap}>
      <button
        ref={triggerRef}
        className={`${styles.emotionDropdownTrigger} ${styles[`emo_${value}`] || styles.emoDefault}`}
        onClick={() => (open ? setOpen(false) : openMenu())}
        type="button"
      >
        {saving ? (
          <Loader2 size={10} className={styles.spinner} />
        ) : saved ? (
          <Check size={10} className={styles.savedIcon} />
        ) : null}
        <span>{value || "—"}</span>
        <ChevronDown
          size={10}
          className={`${styles.dropChevron} ${open ? styles.dropChevronOpen : ""}`}
        />
      </button>

      {open &&
        createPortal(
          <div
            ref={menuRef}
            className={styles.emotionDropdownMenu}
            style={{
              position: "fixed",
              top: menuPos.top,
              left: menuPos.left,
              zIndex: 9999,
            }}
          >
            {options.map((em) => (
              <button
                key={em.value}
                type="button"
                className={`${styles.emotionDropdownItem} ${value === em.value ? styles.emotionDropdownItemActive : ""}`}
                onClick={() => {
                  onChange(em.value);
                  setOpen(false);
                }}
              >
                <span
                  className={`${styles.emotionDot} ${styles[`emoDot_${em.value}`] || styles.emoDotDefault}`}
                />
                {em.label}
                {value === em.value && (
                  <Check size={11} className={styles.dropItemCheck} />
                )}
              </button>
            ))}
          </div>,
          document.body,
        )}
    </div>
  );
}

// ─── editable textarea field ──────────────────────────────────────────────────

interface EditableFieldProps {
  value: string;
  placeholder?: string;
  className?: string;
  onCommit: (val: string) => void;
  saving?: boolean;
  saved?: boolean;
}

function EditableField({
  value,
  placeholder,
  className,
  onCommit,
  saving,
  saved,
}: EditableFieldProps) {
  const [focused, setFocused] = useState(false);
  const [isDirty, setIsDirty] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!focused && ref.current && ref.current.innerText !== value) {
      ref.current.innerText = value;
      setIsDirty(false);
    }
  }, [value, focused]);

  const handleFocus = () => setFocused(true);

  const handleInput = () => {
    setIsDirty((ref.current?.innerText.trim() ?? "") !== value.trim());
  };

  const handleCommit = () => {
    const trimmed = ref.current?.innerText.trim() ?? "";
    setFocused(false);
    setIsDirty(false);
    if (trimmed !== value.trim()) onCommit(trimmed);
    ref.current?.blur();
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLDivElement>) => {
    if (e.key === "Escape") {
      if (ref.current) ref.current.innerText = value;
      setFocused(false);
      setIsDirty(false);
      ref.current?.blur();
    }
  };

  return (
    <div
      className={`${styles.editableWrap} ${focused ? styles.editableWrapFocused : ""}`}
    >
      <div
        ref={ref}
        contentEditable
        suppressContentEditableWarning
        className={`${styles.editableField} ${className ?? ""}`}
        data-placeholder={placeholder}
        onFocus={handleFocus}
        onInput={handleInput}
        onKeyDown={handleKeyDown}
        onBlur={() => {
          if (!isDirty) {
            setFocused(false);
            return;
          }

          if (ref.current) ref.current.innerText = value;
          setFocused(false);
          setIsDirty(false);
        }}
      />

      <div className={styles.editableActions}>
        {saving ? (
          <Loader2 size={13} className={styles.spinner} />
        ) : saved ? (
          <Check size={13} className={styles.savedIcon} />
        ) : isDirty ? (
          <button
            className={styles.commitBtn}
            onMouseDown={(e) => {
              e.preventDefault();
              handleCommit();
            }}
          >
            Edit
          </button>
        ) : null}
      </div>
    </div>
  );
}

// ─── sentence row with inline editing ────────────────────────────────────────

interface SentenceRowEditorProps {
  sent: SentenceEntry;
  sessionId: string;
  emotionChoices: EmotionOption[];
  onSaved: (updated: Partial<SentenceEntry>) => void;
  isGenerated: boolean;
  isPlaying: boolean;
  onVoiceToggle: () => void;
}

function SentenceRowEditor({
  sent,
  sessionId,
  emotionChoices,
  onSaved,
  isGenerated,
  isPlaying,
  onVoiceToggle,
}: SentenceRowEditorProps) {
  const [savedField, setSavedField] = useState<string | null>(null);
  const savedTimer = useRef<ReturnType<typeof setTimeout>>(undefined);

  const mutation = useMutation({
    mutationFn: ({
      field,
      payload,
    }: {
      field: string;
      payload: Partial<SentenceEditState>;
    }) => patchSentence(sessionId, sent.id, payload),
    onSuccess: (data, vars) => {
      onSaved({
        sentence: data.sentence,
        tts_text: data.tts_text,
        emotion: data.emotion,
      });
      setSavedField(vars.field);
      clearTimeout(savedTimer.current);
      savedTimer.current = setTimeout(() => setSavedField(null), 1800);
    },
  });

  const commit = useCallback(
    (field: keyof SentenceEditState, val: string) => {
      const current = (sent[field as keyof SentenceEntry] as string) ?? "";
      if (val === current) return;
      mutation.mutate({ field, payload: { [field]: val } });
    },
    [sent, mutation],
  );

  const isSaving = (f: string) =>
    mutation.isPending && mutation.variables?.field === f;
  const isSaved = (f: string) => savedField === f;

  return (
    <div className={styles.sentenceRow}>
      <div className={styles.sentenceIndex}>
        <span className={styles.chLabel}>Ch{sent.chapter_order}</span>
        <span className={styles.idxLabel}>#{sent.sentence_index}</span>
      </div>

      <div className={styles.sentenceBody}>
        <EditableField
          value={sent.sentence}
          placeholder="Sentence text…"
          className={styles.sentenceText}
          onCommit={(v) => commit("sentence", v)}
          saving={isSaving("sentence")}
          saved={isSaved("sentence")}
        />

        {sent.tts_text && (
          <p className={styles.ttsTextDisplay}>TTS: {sent.tts_text}</p>
        )}

        <EmotionDropdown
          value={sent.emotion ?? "neutral"}
          options={emotionChoices}
          onChange={(v) => commit("emotion", v)}
          saving={isSaving("emotion")}
          saved={isSaved("emotion")}
        />
      </div>

      {isGenerated && sent.voice && (
        <div className={styles.voiceWrap}>
          <audio id={`audio-${sent.id}`} src={sent.voice} />
          <button
            className={`${styles.playBtn} ${isPlaying ? styles.playBtnActive : ""}`}
            onClick={onVoiceToggle}
          >
            {isPlaying ? <Pause size={14} /> : <Play size={14} />}
          </button>
        </div>
      )}
    </div>
  );
}

// ─── main page ────────────────────────────────────────────────────────────────

export default function ProjectDetailPage() {
  const params = useParams();
  const id = params.id as string;
  const router = useRouter();
  const queryClient = useQueryClient();

  const [activeTab, setActiveTab] = useState<Tab>("characters");
  const [playingVoice, setPlayingVoice] = useState<number | null>(null);
  const [expandedProfile, setExpandedProfile] = useState<number | null>(null);

  const { data, isLoading } = useQuery({
    queryKey: ["project-data", id],
    queryFn: () => fetchSessionData(id),
    refetchOnWindowFocus: false,
    enabled: !!id,
  });

  const { data: emotionChoices = [] } = useQuery<EmotionOption[]>({
    queryKey: ["emotion-choices"],
    queryFn: fetchEmotionChoices,
    staleTime: Infinity,
  });

  const handleVoiceToggle = (sentId: number) => {
    const audio = document.getElementById(
      `audio-${sentId}`,
    ) as HTMLAudioElement;
    if (playingVoice === sentId) {
      setPlayingVoice(null);
      audio?.pause();
    } else {
      if (playingVoice !== null) {
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

  const handleSentenceSaved = (
    sentId: number,
    updated: Partial<SentenceEntry>,
  ) => {
    queryClient.setQueryData(["project-data", id], (old: typeof data) => {
      if (!old) return old;
      return {
        ...old,
        sentences: old.sentences.map((s: SentenceEntry) =>
          s.id === sentId ? { ...s, ...updated } : s,
        ),
      };
    });
  };

  if (isLoading || !data) {
    return (
      <div className={styles.loadingState}>
        <div className={styles.loadingBar}>
          <div className={styles.loadingFill} />
        </div>
        <span>Loading Project Data…</span>
      </div>
    );
  }

  const isGenerated = data.is_generation_done;

  const tabs: {
    key: Tab;
    label: string;
    icon: React.ReactNode;
    count: number;
  }[] = [
    {
      key: "characters",
      label: "Characters",
      icon: <User size={15} />,
      count: data.characters.length,
    },
    {
      key: "sentences",
      label: "Sentences",
      icon: <MessageSquare size={15} />,
      count: data.sentences.length,
    },
    {
      key: "scenes",
      label: "Scenes",
      icon: <Image size={15} />,
      count: data.scenes.length,
    },
  ];

  return (
    <div className={styles.container}>
      <header className={styles.header}>
        <button onClick={() => router.back()} className={styles.backBtn}>
          <ChevronLeft size={20} />
        </button>
        <div className={styles.headerInfo}>
          <h1 className={styles.title}>{data.session_name}</h1>
          <div className={styles.headerMeta}>
            <span className={styles.styleBadge}>{data.style}</span>
            <span className={`${styles.statusBadge} ${styles[data.status]}`}>
              {data.status}
            </span>
            {isGenerated && (
              <span className={styles.genBadge}>✦ Generated</span>
            )}
          </div>
        </div>
      </header>

      <div className={styles.statsBar}>
        <div className={styles.statItem}>
          <span className={styles.statNum}>{data.characters.length}</span>
          <span className={styles.statLabel}>Characters</span>
        </div>
        <div className={styles.statDivider} />
        <div className={styles.statItem}>
          <span className={styles.statNum}>{data.sentences.length}</span>
          <span className={styles.statLabel}>Sentences</span>
        </div>
        <div className={styles.statDivider} />
        <div className={styles.statItem}>
          <span className={styles.statNum}>{data.scenes.length}</span>
          <span className={styles.statLabel}>Scenes</span>
        </div>
      </div>

      <div className={styles.tabBar}>
        {tabs.map((t) => (
          <button
            key={t.key}
            className={`${styles.tab} ${activeTab === t.key ? styles.tabActive : ""}`}
            onClick={() => setActiveTab(t.key)}
          >
            {t.icon}
            {t.label}
            <span className={styles.tabCount}>{t.count}</span>
          </button>
        ))}
      </div>

      <div className={styles.content}>
        {/* ============ CHARACTERS ============ */}
        {activeTab === "characters" && (
          <div className={styles.characterList}>
            {data.characters.map((char: CharacterEntry) => (
              <div key={char.profile_id} className={styles.profileCard}>
                <div
                  className={styles.profileHeader}
                  onClick={() =>
                    setExpandedProfile(
                      expandedProfile === char.profile_id
                        ? null
                        : char.profile_id,
                    )
                  }
                >
                  <div className={styles.profileLeft}>
                    <div className={styles.avatarWrap}>
                      {isGenerated && char.master_image ? (
                        // eslint-disable-next-line @next/next/no-img-element
                        <img
                          src={char.master_image}
                          alt={char.name}
                          className={styles.avatarImg}
                        />
                      ) : (
                        <div className={styles.avatarPlaceholder}>
                          <User size={22} />
                        </div>
                      )}
                    </div>
                    <div>
                      <p className={styles.profileName}>{char.name}</p>
                      <p className={styles.profileMeta}>
                        {char.sex && <span>{char.sex}</span>}
                        {char.age && <span> · {char.age}</span>}
                        <span className={styles.emotionCount}>
                          {" "}
                          · {char.emotions.length} emotions
                        </span>
                      </p>
                    </div>
                  </div>
                  <span
                    className={`${styles.chevron} ${expandedProfile === char.profile_id ? styles.chevronOpen : ""}`}
                  >
                    ›
                  </span>
                </div>
                {expandedProfile === char.profile_id && (
                  <div className={styles.emotionGrid}>
                    {char.emotions.map((em) => (
                      <div key={em.character_id} className={styles.emotionItem}>
                        {isGenerated && em.image ? (
                          // eslint-disable-next-line @next/next/no-img-element
                          <img
                            src={em.image}
                            alt={em.emotion}
                            className={styles.emotionImg}
                          />
                        ) : (
                          <div className={styles.emotionImgPlaceholder} />
                        )}
                        <span className={styles.emotionLabel}>
                          {em.emotion}
                        </span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}

        {/* ============ SENTENCES ============ */}
        {activeTab === "sentences" && (
          <div className={styles.sentenceList}>
            {data.sentences.map((sent: SentenceEntry) => (
              <SentenceRowEditor
                key={sent.id}
                sent={sent}
                sessionId={id}
                emotionChoices={emotionChoices}
                isGenerated={isGenerated}
                isPlaying={playingVoice === sent.id}
                onVoiceToggle={() => handleVoiceToggle(sent.id)}
                onSaved={(updated) => handleSentenceSaved(sent.id, updated)}
              />
            ))}
          </div>
        )}

        {/* ============ SCENES ============ */}
        {activeTab === "scenes" && (
          <div className={styles.sceneList}>
            {data.scenes.map((scene: SceneEntry) => (
              <div key={scene.id} className={styles.sceneCard}>
                {isGenerated && scene.image ? (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img
                    src={scene.image}
                    alt={`Scene ${scene.scene_index}`}
                    className={styles.sceneImg}
                  />
                ) : (
                  <div className={styles.sceneImgPlaceholder}>
                    <Image size={28} />
                  </div>
                )}
                <div className={styles.sceneInfo}>
                  <div className={styles.sceneHeader}>
                    <span className={styles.sceneBadge}>
                      Ch{scene.chapter_order} · Scene {scene.scene_index}
                    </span>
                    {scene.sentence_start != null && (
                      <span className={styles.sceneRange}>
                        Sent {scene.sentence_start}–{scene.sentence_end}
                      </span>
                    )}
                  </div>
                  <p className={styles.sceneDesc}>{scene.description || "—"}</p>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
