import { NextResponse } from "next/server";
import { cookies } from "next/headers";
import { serverFetch } from "@/lib/server-api";

// ดึงข้อมูล Profile
export async function GET() {
    const cookieStore = await cookies();
    const accessToken = cookieStore.get("access")?.value;

    if (!accessToken) {
        return NextResponse.json(
            { detail: "Authentication credentials were not provided." },
            { status: 401 }
        );
    }

    const { res, data } = await serverFetch("/user/profile/", {
        headers: {
            Authorization: `Bearer ${accessToken}`,
        },
    });

    return NextResponse.json(data, { status: res.status });
}

export async function PUT(request: Request) {
    const body = await request.json();
    const cookieStore = await cookies();
    const accessToken = cookieStore.get("access")?.value;

    if (!accessToken) {
        return NextResponse.json(
            { detail: "Authentication credentials were not provided." },
            { status: 401 }
        );
    }

    const { res, data } = await serverFetch("/user/profile/", {
        method: "PUT",
        body: JSON.stringify(body),
        headers: {
            Authorization: `Bearer ${accessToken}`,
            "Content-Type": "application/json",
        },
    });

    return NextResponse.json(data, { status: res.status });
}

export async function DELETE(request: Request) {
    const body = await request.json().catch(() => ({}));

    const cookieStore = await cookies();
    const accessToken = cookieStore.get("access")?.value;

    if (!accessToken) {
        return NextResponse.json(
            { detail: "Authentication credentials were not provided." },
            { status: 401 }
        );
    }

    const { res, data } = await serverFetch("/user/profile/", {
        method: "DELETE",
        body: JSON.stringify(body),
        headers: {
            Authorization: `Bearer ${accessToken}`,
            "Content-Type": "application/json",
        },
    });

    if (res.status === 204) {
        return new NextResponse(null, { status: 204 });
    }

    return NextResponse.json(data, { status: res.status });
}