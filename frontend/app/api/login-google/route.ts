import { NextResponse } from "next/server";
import { serverFetch } from "@/lib/server-api";

export async function POST(req: Request) {
  const body = await req.json();

  const { res, data } = await serverFetch("/user/login-google/", {
    method: "POST",
    body: JSON.stringify(body),
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

  response.cookies.set("refresh", data.refresh, {
    httpOnly: true,
    secure: true,
    sameSite: "lax",
    path: "/",
  });

  return response;
}