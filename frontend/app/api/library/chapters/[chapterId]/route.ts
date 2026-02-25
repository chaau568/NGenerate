import { NextResponse } from "next/server";
import { cookies } from "next/headers";
import { serverFetch } from "@/lib/server-api";

type Context = { params: Promise<{ chapterId: string }> };

export async function GET(request: Request, context: Context) {
    const { chapterId } = await context.params;
    const cookieStore = await cookies();
    const accessToken = cookieStore.get("access")?.value;

    const { res, data } = await serverFetch(`/library/chapters/${chapterId}/`, {
        headers: { Authorization: `Bearer ${accessToken}` },
    });
    return NextResponse.json(data, { status: res.status });
}

export async function PUT(request: Request, context: Context) {
    const { chapterId } = await context.params;
    const body = await request.json();
    const cookieStore = await cookies();
    const accessToken = cookieStore.get("access")?.value;

    const { res, data } = await serverFetch(`/library/chapters/${chapterId}/`, {
        method: "PUT",
        body: JSON.stringify(body),
        headers: { Authorization: `Bearer ${accessToken}` },
    });
    return NextResponse.json(data, { status: res.status });
}

export async function DELETE(request: Request, context: Context) {
    const { chapterId } = await context.params;
    const cookieStore = await cookies();
    const accessToken = cookieStore.get("access")?.value;

    const { res } = await serverFetch(`/library/chapters/${chapterId}/`, {
        method: "DELETE",
        headers: { Authorization: `Bearer ${accessToken}` },
    });
    return new NextResponse(null, { status: res.status });
}