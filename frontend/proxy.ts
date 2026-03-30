import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

export async function proxy(req: NextRequest) {
  const token = req.cookies.get("access")?.value;
  const { pathname } = req.nextUrl;

  // 🔓 PUBLIC
  if (pathname.startsWith("/login") || pathname.startsWith("/register")) {
    if (token) {
      try {
        const res = await fetch(
          `${process.env.NEXT_PUBLIC_API_BASE_URL}/user/profile/`,
          {
            headers: {
              Authorization: `Bearer ${token}`,
            },
          }
        );

        if (!res.ok) return NextResponse.next();

        const user = await res.json();

        if (user.role === "admin") {
          return NextResponse.redirect(
            new URL("/main-dashboard", req.url)
          );
        }

        return NextResponse.redirect(new URL("/library", req.url));
      } catch {
        return NextResponse.next();
      }
    }

    return NextResponse.next();
  }

  // 🔐 PROTECTED
  if (
    pathname.startsWith("/library") ||
    pathname.startsWith("/project") ||
    pathname.startsWith("/notification") ||
    pathname.startsWith("/package") ||
    pathname.startsWith("/profile") ||
    pathname.startsWith("/transaction") ||
    pathname.startsWith("/main-dashboard") ||
    pathname.startsWith("/activity-dashboard")
  ) {
    if (!token) {
      return NextResponse.redirect(new URL("/login", req.url));
    }

    try {
      const res = await fetch(
        `${process.env.NEXT_PUBLIC_API_BASE_URL}/user/profile/`,
        {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        }
      );

      if (!res.ok) {
        return NextResponse.redirect(new URL("/login", req.url));
      }

      const user = await res.json();

      // ❗ กัน user เข้า admin pages
      if (
        (pathname.startsWith("/main-dashboard") ||
          pathname.startsWith("/activity-dashboard")) &&
        user.role !== "admin"
      ) {
        return NextResponse.redirect(new URL("/403", req.url));
      }

      return NextResponse.next();
    } catch {
      return NextResponse.redirect(new URL("/login", req.url));
    }
  }

  return NextResponse.next();
}

export const config = {
  matcher: [
    "/login",
    "/register",

    "/library/:path*",
    "/notification/:path*",
    "/package/:path*",
    "/profile/:path*",
    "/project/:path*",
    "/transaction/:path*",

    "/main-dashboard/:path*",
    "/activity-dashboard/:path*",
  ],
};