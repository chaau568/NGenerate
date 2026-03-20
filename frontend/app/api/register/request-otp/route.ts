import { NextResponse } from "next/server";
import { serverFetch } from "@/lib/server-api";

export async function POST(request: Request) {
    const body = await request.json();

    const { res, data } = await serverFetch("/user/register/request-otp/", {
        method: "POST",
        body: JSON.stringify(body),
    });

    return NextResponse.json(data, { status: res.status });
}
