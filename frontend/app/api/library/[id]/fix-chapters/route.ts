import { NextResponse } from "next/server";
import { cookies } from "next/headers";
import { serverFetch } from "@/lib/server-api";

type Context = {
    params: Promise<{ id: string }>;
};

export async function POST(
    request: Request,
    context: Context
) {
    const { id } = await context.params;
    const cookieStore = await cookies();
    const accessToken = cookieStore.get("access")?.value;

    if (!accessToken) {
        return NextResponse.json({ detail: "Unauthorized" }, { status: 401 });
    }

    const body = await request.json();

    const { res, data } = await serverFetch(
        `/library/${id}/fix-chapters/`,
        {
            method: "POST",
            headers: {
                Authorization: `Bearer ${accessToken}`,
                "Content-Type": "application/json",
            },
            body: JSON.stringify(body),
        }
    );

    return NextResponse.json(data, { status: res.status });
}