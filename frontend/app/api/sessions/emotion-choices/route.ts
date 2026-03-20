import { NextResponse } from "next/server";
import { serverFetch } from "@/lib/server-api";
import { cookies } from "next/headers";

export async function GET() {
  const cookieStore = await cookies();
  const accessToken = cookieStore.get("access")?.value;

  if (!accessToken) {
    return NextResponse.json(
      { detail: "Authentication credentials were not provided." },
      { status: 401 },
    );
  }

  const { res, data } = await serverFetch("/session/emotion-choices/", {
    headers: { Authorization: `Bearer ${accessToken}` },
  });

  return NextResponse.json(data, { status: res.status });
}