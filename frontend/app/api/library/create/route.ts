import { NextResponse } from "next/server";
import { cookies } from "next/headers";

export async function POST(request: Request) {
    try {
        const cookieStore = await cookies();
        const accessToken = cookieStore.get("access")?.value;

        if (!accessToken) {
            return NextResponse.json({ detail: "Unauthorized" }, { status: 401 });
        }

        const formData = await request.formData();

        const apiUrl = `${process.env.NEXT_PUBLIC_API_BASE_URL}/library/create/`;

        const res = await fetch(apiUrl, {
            method: "POST",
            headers: {
                Authorization: `Bearer ${accessToken}`,
            },
            body: formData,
        });

        const data = await res.json();

        if (!res.ok) {
            return NextResponse.json(data, { status: res.status });
        }

        return NextResponse.json(data);
    } catch (err: any) {
        console.error("Create novel error:", err);
        return NextResponse.json(
            { error: "Internal Server Error", detail: err.message },
            { status: 500 }
        );
    }
}