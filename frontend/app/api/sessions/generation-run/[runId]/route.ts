import { NextResponse } from "next/server";
import { serverFetch } from "@/lib/server-api";
import { cookies } from "next/headers";

export async function DELETE(
    req: Request,
    context: { params: Promise<{ runId: string }> }
) {
    const { runId } = await context.params;
    const cookieStore = await cookies();
    const accessToken = cookieStore.get("access")?.value;

    if (!accessToken) {
        return NextResponse.json({ detail: "Unauthorized" }, { status: 401 });
    }

    const { res } = await serverFetch(
        `/session/generation-run/${runId}/delete/`,
        {
            method: "DELETE",
            headers: { Authorization: `Bearer ${accessToken}` },
        }
    );

    return new NextResponse(null, { status: res.status });
}