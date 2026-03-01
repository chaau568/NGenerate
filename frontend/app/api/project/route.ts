import { NextResponse } from "next/server";
import { serverFetch } from "@/lib/server-api";
import { cookies } from "next/headers";

export async function GET(request: Request) {
    const { searchParams } = new URL(request.url);
    const type = searchParams.get("type");

    const cookieStore = await cookies();
    const accessToken = cookieStore.get("access")?.value;

    if (!accessToken) {
        return NextResponse.json(
            { detail: "Authentication credentials were not provided." },
            { status: 401 }
        );
    }

    const endpoint =
        type === "current"
            ? "/session/current-tasks/"
            : "/session/finished-tasks/";

    const { res, data } = await serverFetch(endpoint, {
        headers: {
            Authorization: `Bearer ${accessToken}`,
        },
    });

    return NextResponse.json(data, { status: res.status });
}