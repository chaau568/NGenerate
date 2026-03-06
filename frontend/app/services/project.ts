import { clientFetch } from "@/lib/client-fetch";

/* ================= CURRENT ================= */

export interface CurrentTask {
    session_id: number;
    novel_id: number;
    session_name: string;
    status: string;
    progress: number;
}

export const fetchCurrentTasks = async (): Promise<{
    current_tasks: CurrentTask[];
}> => {
    const res = await clientFetch("/api/project?type=current");

    if (!res.ok) {
        const error = await res.json().catch(() => null);
        throw new Error(error?.detail || "Failed to fetch current tasks");
    }

    return res.json();
};

/* ================= FINISHED ================= */

export interface AnalysisHistory {
    session_id: number;
    novel_id: number;
    session_name: string;
    status: string;
    created_at?: string;
    analysis_finished_at?: string;
    cover: string | null;
}

export interface GenerationHistory {
    session_id: number;
    novel_id: number;
    session_name: string;
    status: string;
    version: string;
    file_size: number;
    created_at?: string;
    generation_finished_at?: string;
    cover: string | null;
    video_id: number;
}

export interface FailedHistory {
    session_id: number;
    novel_id: number;
    session_name: string;
    status: string;
    created_at?: string;
    cover: string | null;
}

export const fetchFinishedTasks = async (): Promise<{
    analysis_history: AnalysisHistory[];
    generation_history: GenerationHistory[];
    failed_history: FailedHistory[];
}> => {
    const res = await clientFetch("/api/project?type=finished");

    if (!res.ok) {
        const error = await res.json().catch(() => null);
        throw new Error(error?.detail || "Failed to fetch finished tasks");
    }

    return res.json();
};