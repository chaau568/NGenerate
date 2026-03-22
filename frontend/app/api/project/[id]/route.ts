import { NextResponse } from "next/server";
import { serverFetch } from "@/lib/server-api";
import { cookies } from "next/headers";

export async function POST(
    request: Request,
    { params }: { params: Promise<{ id: string }> }
) {
    const { id } = await params;

    const cookieStore = await cookies();
    const accessToken = cookieStore.get("access")?.value;

    if (!accessToken) {
        return NextResponse.json(
            { detail: "Authentication credentials were not provided." },
            { status: 401 }
        );
    }

    const body = await request.json();
    const { chapter_ids, session_type } = body;

    const { res, data } = await serverFetch(
        `/session/create/${id}/`,
        {
            method: "POST",
            headers: {
                Authorization: `Bearer ${accessToken}`,
            },
            body: JSON.stringify({
                chapter_ids,
                session_type,
            }),
        }
    );

    return NextResponse.json(data, { status: res.status });
}

export async function GET(
    req: Request,
    context: { params: Promise<{ id: string }> }
) {
    const { id } = await context.params;
    const { searchParams } = new URL(req.url);

    const watchVideoId = searchParams.get("watch");
    const downloadVideoId = searchParams.get("download");

    const cookieStore = await cookies();
    const accessToken = cookieStore.get("access")?.value;

    if (!accessToken) {
        return NextResponse.json(
            { detail: "Authentication credentials were not provided." },
            { status: 401 }
        );
    }

    /* ================= WATCH ================= */
    if (watchVideoId) {
        const rangeHeader = req.headers.get("range");

        const fetchHeaders: Record<string, string> = {
            Authorization: `Bearer ${accessToken}`,
        };
        if (rangeHeader) {
            fetchHeaders["Range"] = rangeHeader;
        }

        const { res } = await serverFetch(
            `/asset/videos/${watchVideoId}/watch/`,
            {
                headers: fetchHeaders,
                raw: true,
            }
        );

        if (!res.ok && res.status !== 206) {
            return NextResponse.json(
                { detail: "Watch failed" },
                { status: res.status }
            );
        }

        const responseHeaders: Record<string, string> = {
            "Content-Type": res.headers.get("Content-Type") || "video/mp4",
            "Accept-Ranges": "bytes",
        };

        const contentRange = res.headers.get("Content-Range");
        const contentLength = res.headers.get("Content-Length");
        if (contentRange) responseHeaders["Content-Range"] = contentRange;
        if (contentLength) responseHeaders["Content-Length"] = contentLength;

        return new NextResponse(res.body, {
            status: res.status,
            headers: responseHeaders,
        });
    }

    /* ================= DOWNLOAD ================= */
    if (downloadVideoId) {
        const { res } = await serverFetch(
            `/asset/videos/${downloadVideoId}/download/`,
            {
                headers: {
                    Authorization: `Bearer ${accessToken}`,
                },
                raw: true,
            }
        );

        if (!res.ok) {
            return NextResponse.json(
                { detail: "Download failed" },
                { status: res.status }
            );
        }

        return new NextResponse(res.body, {
            status: 200,
            headers: {
                "Content-Type":
                    res.headers.get("Content-Type") ||
                    "application/octet-stream",
                "Content-Disposition":
                    res.headers.get("Content-Disposition") ||
                    `attachment; filename="video-${downloadVideoId}.mp4"`,
            },
        });
    }

    /* ================= SESSION DETAIL ================= */
    const { res, data } = await serverFetch(
        `/session/detail/${id}/`,
        {
            headers: {
                Authorization: `Bearer ${accessToken}`,
            },
        }
    );

    if (!res.ok) {
        return NextResponse.json(data, { status: res.status });
    }

    return NextResponse.json(data);
}

export async function DELETE(
    req: Request,
    context: { params: Promise<{ id: string }> }
) {
    const { id } = await context.params;

    const cookieStore = await cookies();
    const accessToken = cookieStore.get("access")?.value;

    if (!accessToken) {
        return NextResponse.json({ detail: "Unauthorized" }, { status: 401 });
    }

    const { res } = await serverFetch(
        `/session/delete/${id}/`,
        {
            method: "DELETE",
            headers: {
                Authorization: `Bearer ${accessToken}`,
            },
        }
    );

    return new NextResponse(null, { status: res.status });
}