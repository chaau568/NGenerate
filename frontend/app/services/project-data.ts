import { clientFetch } from "@/lib/client-fetch";

export type SceneCharacter = {
    id: number
    name: string;
    action: string;
    expression: string;
    image?: string
};

export type SceneSentence = {
    id: number;
    sentence_index: number;
    sentence: string;
    tts_text: string;
    voice: string | null;
};

export type SceneEntry = {
    id: number;
    chapter_order: number;
    scene_index: number;
    description: string;
    image: string | null;
    characters: SceneCharacter[];
    sentences: SceneSentence[];
};

export type SessionData = {
    session_id: number;
    session_name: string;
    session_type: string;
    style: string;
    status: string;
    is_analysis_done: boolean;
    is_generation_done: boolean;

    scenes: SceneEntry[];
};

export const fetchSessionData = async (
    id: string | number
): Promise<SessionData> => {
    const res = await clientFetch(`/api/sessions/data/${id}`);
    if (!res.ok) throw new Error("Failed to fetch session data");
    return res.json();
};