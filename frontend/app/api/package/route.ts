import { NextResponse } from "next/server";
import { cookies } from "next/headers";
import { serverFetch } from "@/lib/server-api";

export async function GET() {
    const cookieStore = await cookies();
    const accessToken = cookieStore.get("access")?.value;

    if (!accessToken) {
        return NextResponse.json(
            { detail: "Authentication credentials were not provided." },
            { status: 401 }
        );
    }

    const { res, data } = await serverFetch("/payment/package/", {
        headers: {
            Authorization: `Bearer ${accessToken}`,
        },
    });

    return NextResponse.json(data, { status: res.status });
}

export async function POST(req: Request) {
    const cookieStore = await cookies();
    const accessToken = cookieStore.get("access")?.value;

    const body = await req.json();
    const { package_id } = body;

    if (!accessToken) {
        return NextResponse.json(
            { detail: "Authentication credentials were not provided." },
            { status: 401 }
        );
    }


    const { res, data } = await serverFetch(`/payment/create/`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${accessToken}`,
        },
        body: JSON.stringify({ package_id }),
    });

    return NextResponse.json(data, { status: res.status });
}