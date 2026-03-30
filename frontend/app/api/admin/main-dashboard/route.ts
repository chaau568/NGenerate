import { NextResponse } from "next/server";
import { serverFetch } from "@/lib/server-api";
import { cookies } from "next/headers";

export async function GET() {
    const cookieStore = await cookies();
    const accessToken = cookieStore.get("access")?.value;

    if (!accessToken) {
        return NextResponse.json({ detail: "Unauthorized" }, { status: 401 });
    }

    const { res, data } = await serverFetch("/admin-console/main-dashboard/", {
        headers: { Authorization: `Bearer ${accessToken}` },
    });

    return NextResponse.json(data, { status: res.status });
}