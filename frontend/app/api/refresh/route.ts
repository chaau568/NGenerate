import { NextResponse } from "next/server";
import { cookies } from "next/headers";
import { serverFetch } from "@/lib/server-api";

export async function POST() {
  const cookieStore = await cookies();
  const refresh = cookieStore.get("refresh")?.value;

  if (!refresh) {
    return NextResponse.json(
      { error: "No refresh token" },
      { status: 401 }
    );
  }

  const { res, data } = await serverFetch("/api/token/refresh/", {
    method: "POST",
    body: JSON.stringify({ refresh }),
  });

  if (!res.ok) {
    return NextResponse.json(data, { status: res.status });
  }

  const response = NextResponse.json({ success: true });

  response.cookies.set("access", data.access, {
    httpOnly: true,
    secure: true,
    sameSite: "lax",
    path: "/",
  });

  return response;
}