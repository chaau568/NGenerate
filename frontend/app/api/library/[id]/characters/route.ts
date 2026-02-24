import { NextResponse } from "next/server";
import { cookies } from "next/headers";
import { serverFetch } from "@/lib/server-api";

type Context = {
    params: Promise<{ id: string }>;
};

export async function GET(
    request: Request,
    context: Context
) {
    const { id } = await context.params
    const cookieStore = await cookies();
    const accessToken = cookieStore.get("access")?.value;

    if (!accessToken) {
        return NextResponse.json({ detail: "Unauthorized" }, { status: 401 });
    }

    const { res, data } = await serverFetch(
        `/library/${id}/characters/`,
        {
            method: "GET",
            headers: {
                Authorization: `Bearer ${accessToken}`,
            },
        }
    );

    return NextResponse.json(data, { status: res.status });
}