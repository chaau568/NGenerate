import { NextResponse } from "next/server";
import { serverFetch } from "@/lib/server-api";
import { cookies } from "next/headers";

export async function POST(req: Request) {
    const body = await req.json();
    console.log("verify body received:", body);
    const { email, otp } = body;

    if (!email || !otp) {
        return NextResponse.json(
            { error: "email and otp are required" },
            { status: 400 }
        );
    }

    const { res, data } = await serverFetch("/user/login-google/verify/", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, otp }),
    });

    if (!res.ok) {
        return NextResponse.json(data, { status: res.status });
    }

    const cookieStore = await cookies();
    cookieStore.set("access", data.access, {
        httpOnly: true,
        secure: process.env.NODE_ENV === "production",
        sameSite: "lax",
        maxAge: 60 * 30, // 30 นาที
    });
    cookieStore.set("refresh", data.refresh, {
        httpOnly: true,
        secure: process.env.NODE_ENV === "production",
        sameSite: "lax",
        maxAge: 60 * 60 * 24 * 7, // 7 วัน
    });

    return NextResponse.json({ success: true }, { status: 200 });
}
