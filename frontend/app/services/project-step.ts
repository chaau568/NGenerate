import { clientFetch } from "@/lib/client-fetch";

export type ProjectStepStatus =
    | "pending"
    | "processing"
    | "success"
    | "failed";

export type ProjectStep = {
    id: number;
    name: string;
    status: ProjectStepStatus;
    started_at: string | null;
    finished_at: string | null;
    error_message: string | null;
};

export type ProjectDetail = {
    session_name: string;
    status: string;
    overall_progress: number;
    started_at: string;
    steps: ProjectStep[];
};

export const fetchProjectDetail = async (
    id: string | number
): Promise<ProjectDetail> => {
    const res = await clientFetch(`/api/project/${id}`);
    if (!res.ok) throw new Error("Failed to fetch project detail");

    const json = await res.json();
    return json;
};