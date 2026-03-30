import { NextResponse } from "next/server";
import { serverFetch } from "@/lib/server-api";
import { cookies } from "next/headers";

export async function GET(request: Request) {
    const { searchParams } = new URL(request.url);
    const page = searchParams.get("page") ?? "1";
    const type = searchParams.get("type") ?? "all";
    const status = searchParams.get("status") ?? "all";

    const cookieStore = await cookies();
    const accessToken = cookieStore.get("access")?.value;

    if (!accessToken) {
        return NextResponse.json({ detail: "Unauthorized" }, { status: 401 });
    }

    const query = new URLSearchParams({ page, type, status }).toString();

    const { res, data } = await serverFetch(`/admin-console/activity-dashboard/?${query}`, {
        headers: { Authorization: `Bearer ${accessToken}` },
    });

    return NextResponse.json(data, { status: res.status });
}