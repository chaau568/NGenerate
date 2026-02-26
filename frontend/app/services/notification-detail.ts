import { clientFetch } from "@/lib/client-fetch";

export type ProcessingStep = {
    id: number;
    name: string;
    status: "pending" | "analyzing" | "analyzed" | "fail";
    started_at: string | null;
    finished_at: string | null;
    error_message: string | null;
};

export type NotificationDetail = {
    id: number;
    task_name: string;
    status: string;
    message: string;
    is_read: boolean;
    created_at: string;
    processing: {
        overall_progress: number;
        started_at: string;
        steps: ProcessingStep[];
    } | null;
    session_info: any;
    novel_info: any;
};

export const fetchNotificationDetail = async (
    id: string | number
): Promise<NotificationDetail> => {
    const res = await clientFetch(`/api/notification/${id}`);
    if (!res.ok) throw new Error("Failed to fetch detail");

    const json = await res.json();

    return json.data;
};