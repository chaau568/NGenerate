import { NextResponse } from "next/server";
import { serverFetch } from "@/lib/server-api";

export async function POST(request: Request) {
  const body = await request.json();

  const { res, data } = await serverFetch("/user/login/", {
    method: "POST",
    body: JSON.stringify(body),
  });

  if (!res.ok) {
    return NextResponse.json(data, { status: res.status });
  }

  const response = NextResponse.json({ success: true, role: data.role, });

  response.cookies.set("access", data.access, {
    httpOnly: true,
    secure: true,
    sameSite: "lax",
    path: "/",
  });

  response.cookies.set("refresh", data.refresh, {
    httpOnly: true,
    secure: true,
    sameSite: "lax",
    path: "/",
  });

  return response;
}