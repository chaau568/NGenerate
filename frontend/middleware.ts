import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

export function middleware(request: NextRequest) {
  const access = request.cookies.get("access");

  const protectedPaths = ["/library", "/session", "/admin"];

  const isProtected = protectedPaths.some((path) =>
    request.nextUrl.pathname.startsWith(path)
  );

  if (isProtected && !access) {
    return NextResponse.redirect(new URL("/login", request.url));
  }

  return NextResponse.next();
}