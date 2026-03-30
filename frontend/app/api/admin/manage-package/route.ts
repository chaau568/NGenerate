import { NextResponse } from "next/server";
import { serverFetch } from "@/lib/server-api";
import { cookies } from "next/headers";

async function getAuth() {
    const cookieStore = await cookies();
    const accessToken = cookieStore.get("access")?.value;
    return accessToken;
}

// GET /api/admin/manage-package  →  list all packages
export async function GET() {
    const accessToken = await getAuth();
    if (!accessToken) return NextResponse.json({ detail: "Unauthorized" }, { status: 401 });

    const { res, data } = await serverFetch("/payment/packages/all/", {
        headers: { Authorization: `Bearer ${accessToken}` },
    });
    return NextResponse.json(data, { status: res.status });
}

// POST /api/admin/manage-package  →  create package
export async function POST(request: Request) {
    const accessToken = await getAuth();
    if (!accessToken) return NextResponse.json({ detail: "Unauthorized" }, { status: 401 });

    const body = await request.json();
    const { res, data } = await serverFetch("/payment/packages/create/", {
        method: "POST",
        headers: {
            Authorization: `Bearer ${accessToken}`,
            "Content-Type": "application/json",
        },
        body: JSON.stringify(body),
    });
    return NextResponse.json(data, { status: res.status });
}