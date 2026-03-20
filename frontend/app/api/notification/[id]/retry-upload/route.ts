import { NextResponse } from "next/server";
import { serverFetch } from "@/lib/server-api";
import { cookies } from "next/headers";

// POST /api/notification/[id]/retry-upload
// → Django: POST /novels/<novel_id>/retry-upload/<notification_id>/
export async function POST(
    req: Request,
    context: { params: Promise<{ id: string }> }
) {
    const { id: notificationId } = await context.params;
    const cookieStore = await cookies();
    const accessToken = cookieStore.get("access")?.value;

    if (!accessToken) {
        return NextResponse.json(
            { detail: "Authentication credentials were not provided." },
            { status: 401 }
        );
    }

    const body = await req.json().catch(() => ({}));
    const novelId = body.novel_id;

    if (!novelId) {
        return NextResponse.json(
            { error: "novel_id is required" },
            { status: 400 }
        );
    }

    const { res, data } = await serverFetch(
        `/library/${novelId}/retry-upload/${notificationId}/`,
        {
            method: "POST",
            headers: {
                Authorization: `Bearer ${accessToken}`,
            },
        }
    );

    return NextResponse.json(data, { status: res.status });
}