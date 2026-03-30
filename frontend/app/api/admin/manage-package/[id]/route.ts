import { NextResponse } from "next/server";
import { serverFetch } from "@/lib/server-api";
import { cookies } from "next/headers";

async function getAuth() {
    const cookieStore = await cookies();
    const accessToken = cookieStore.get("access")?.value;
    return accessToken;
}

// PATCH /api/admin/manage-package/[id]  →  update package
export async function PATCH(
    request: Request,
    { params }: { params: Promise<{ id: string }> }
) {
    const { id } = await params; // ⭐ FIX

    const accessToken = await getAuth();
    if (!accessToken)
        return NextResponse.json({ detail: "Unauthorized" }, { status: 401 });

    const body = await request.json();

    const { res, data } = await serverFetch(`/payment/packages/${id}/`, {
        method: "PATCH",
        headers: {
            Authorization: `Bearer ${accessToken}`,
            "Content-Type": "application/json",
        },
        body: JSON.stringify(body),
    });

    return NextResponse.json(data, { status: res.status });
}

// DELETE /api/admin/manage-package/[id]  →  delete package
export async function DELETE(
    _request: Request,
    { params }: { params: Promise<{ id: string }> }
) {
    const { id } = await params; // ⭐ FIX

    const accessToken = await getAuth();
    if (!accessToken)
        return NextResponse.json({ detail: "Unauthorized" }, { status: 401 });

    const { res, data } = await serverFetch(`/payment/packages/${id}/delete/`, {
        method: "DELETE",
        headers: { Authorization: `Bearer ${accessToken}` },
    });

    if (res.status === 204) return new NextResponse(null, { status: 204 });

    return NextResponse.json(data, { status: res.status });
}