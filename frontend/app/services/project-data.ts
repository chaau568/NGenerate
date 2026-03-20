import { clientFetch } from "@/lib/client-fetch";

export type EmotionEntry = {
    character_id: number;
    emotion: string;
    image: string | null;
};

export type CharacterEntry = {
    profile_id: number;
    name: string;
    appearance: string;
    sex: string;
    age: string;
    master_image: string | null;
    emotions: EmotionEntry[];
};

export type SentenceEntry = {
    id: number;
    chapter_order: number;
    sentence_index: number;
    sentence: string;
    tts_text: string;
    emotion: string;
    voice: string | null;
};

export type SceneEntry = {
    id: number;
    chapter_order: number;
    scene_index: number;
    sentence_start: number | null;
    sentence_end: number | null;
    description: string;
    image: string | null;
};

export type SessionData = {
    session_id: number;
    session_name: string;
    session_type: string;
    style: string;
    status: string;
    is_analysis_done: boolean;
    is_generation_done: boolean;
    characters: CharacterEntry[];
    sentences: SentenceEntry[];
    scenes: SceneEntry[];
};

export const fetchSessionData = async (id: string | number): Promise<SessionData> => {
    const res = await clientFetch(`/api/sessions/data/${id}`);
    if (!res.ok) throw new Error("Failed to fetch session data");
    return res.json();
};