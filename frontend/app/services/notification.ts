import { clientFetch } from "@/lib/client-fetch";

export type Notification = {
    id: number;
    task_type: string;
    status: string;
    message: string;
    is_read: boolean;
    created_at: string;
    type: "novel" | "session";
    ref_id: number;
};

export const fetchNotifications = async (): Promise<Notification[]> => {
    const res = await clientFetch("/api/notification");
    if (!res.ok) throw new Error("Failed to fetch notifications");

    const data = await res.json();

    return [...data.notifications].sort(
        (a, b) =>
            new Date(b.created_at).getTime() -
            new Date(a.created_at).getTime(),
    );
};

export const fetchUnreadCount = async (): Promise<number> => {
    const res = await clientFetch("/api/notification/unread-count");
    if (!res.ok) throw new Error("Failed to fetch unread count");

    const data = await res.json();
    return data.count;
};