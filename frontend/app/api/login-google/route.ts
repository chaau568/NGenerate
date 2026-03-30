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

  // Step 1 — ยังไม่ set cookie เพราะยังไม่มี JWT
  // แค่ส่ง email กลับให้ frontend เพื่อแสดงหน้า OTP
  return NextResponse.json(
    { email: data.email, message: data.message },
    { status: 200 }
  );
}