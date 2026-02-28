import { NextResponse } from "next/server";
import { cookies } from "next/headers";
import { serverFetch } from "@/lib/server-api";

export async function GET(req: Request) {
    const { searchParams } = new URL(req.url);
    const type = searchParams.get("type"); // billing | activity

    const cookieStore = await cookies();
    const accessToken = cookieStore.get("access")?.value;

    if (!accessToken) {
        return NextResponse.json(
            { detail: "Authentication credentials were not provided." },
            { status: 401 }
        );
    }

    let endpoint = "";

    if (type === "billing") {
        endpoint = "/payment/my-payments/";
    } else if (type === "activity") {
        endpoint = "/payment/my-credit-logs/";
    } else {
        return NextResponse.json(
            { detail: "Invalid type" },
            { status: 400 }
        );
    }

    const { res, data } = await serverFetch(endpoint, {
        method: "GET",
        headers: {
            Authorization: `Bearer ${accessToken}`,
        },
    });

    return NextResponse.json(data, { status: res.status });
}