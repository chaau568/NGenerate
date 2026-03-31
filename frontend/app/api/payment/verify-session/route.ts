import { NextResponse } from "next/server";
import { cookies } from "next/headers";
import { serverFetch } from "@/lib/server-api";

export async function POST(req: Request) {
    const cookieStore = await cookies();
    const accessToken = cookieStore.get("access")?.value;

    if (!accessToken) {
        return NextResponse.json(
            { detail: "Unauthorized" },
            { status: 401 }
        );
    }

    const body = await req.json();
    const { session_id } = body;

    if (!session_id) {
        return NextResponse.json(
            { error: "session_id is required" },
            { status: 400 }
        );
    }

    const { res, data } = await serverFetch(
        "/payment/webhook/stripe/verify_session",
        {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                Authorization: `Bearer ${accessToken}`,
            },
            body: JSON.stringify({ session_id }),
        }
    );

    return NextResponse.json(data, { status: res.status });
}