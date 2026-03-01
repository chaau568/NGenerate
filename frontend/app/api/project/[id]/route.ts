import { NextResponse } from "next/server";
import { serverFetch } from "@/lib/server-api";
import { cookies } from "next/headers";

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
        const { res } = await serverFetch(
            `/asset/videos/${watchVideoId}/watch/`,
            {
                headers: {
                    Authorization: `Bearer ${accessToken}`,
                },
                raw: true, // 👈 สำคัญ ถ้า serverFetch รองรับ
            }
        );

        if (!res.ok) {
            return NextResponse.json(
                { detail: "Watch failed" },
                { status: res.status }
            );
        }

        return new NextResponse(res.body, {
            status: 200,
            headers: {
                "Content-Type":
                    res.headers.get("Content-Type") || "video/mp4",
                "Content-Disposition":
                    res.headers.get("Content-Disposition") || "inline",
            },
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