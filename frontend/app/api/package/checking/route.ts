import { NextResponse } from "next/server";
import { serverFetch } from "@/lib/server-api";
import { cookies } from "next/headers";

export async function GET(req: Request) {
    const { searchParams } = new URL(req.url);
    const transactionId = searchParams.get("transaction_id");

    if (!transactionId) {
        return NextResponse.json(
            { detail: "transaction_id is required" },
            { status: 400 }
        );
    }

    const cookieStore = await cookies();
    const accessToken = cookieStore.get("access")?.value;

    if (!accessToken) {
        return NextResponse.json(
            { detail: "Authentication credentials were not provided." },
            { status: 401 }
        );
    }

    const { res, data } = await serverFetch(
        `/payment/checking/${transactionId}/`,
        {
            headers: {
                Authorization: `Bearer ${accessToken}`,
            },
        }
    );

    return NextResponse.json(data, { status: res.status });
}