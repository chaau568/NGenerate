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
    const { id } = await context.params; 

    const cookieStore = await cookies();
    const accessToken = cookieStore.get("access")?.value;

    if (!accessToken) {
        return NextResponse.json({ detail: "Unauthorized" }, { status: 401 });
    }

    const { res, data } = await serverFetch(`/library/${id}/`, {
        method: "GET",
        headers: {
            Authorization: `Bearer ${accessToken}`,
        },
    });

    return NextResponse.json(data, { status: res.status });
}

export async function DELETE(
    request: Request,
    context: Context
) {
    const { id } = await context.params;

    const cookieStore = await cookies();
    const accessToken = cookieStore.get("access")?.value;

    if (!accessToken) {
        return NextResponse.json({ detail: "Unauthorized" }, { status: 401 });
    }

    const { res } = await serverFetch(`/library/${id}/`, {
        method: "DELETE",
        headers: {
            Authorization: `Bearer ${accessToken}`,
        },
    });

    if (res.status === 204) {
        return new NextResponse(null, { status: 204 });
    }

    return NextResponse.json(
        { detail: "Delete failed" },
        { status: res.status }
    );
}

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

    const contentType = request.headers.get("content-type") || "";

    let body: any;

    if (contentType.includes("multipart/form-data")) {
        body = await request.formData();
    } else {
        body = JSON.stringify(await request.json());
    }

    const { res, data } = await serverFetch(
        `/library/${id}/chapters/`,
        {
            method: "POST",
            headers: {
                Authorization: `Bearer ${accessToken}`,
                ...(contentType.includes("application/json") && {
                    "Content-Type": "application/json",
                }),
            },
            body,
        }
    );

    return NextResponse.json(data, { status: res.status });
}