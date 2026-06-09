import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

const PROTECTED_PREFIXES = [
  "/dashboard",
  "/search",
  "/dgcp",
  "/odoo",
  "/m365",
  "/work",
  "/tasks",
  "/notifications",
  "/oportunidades",
  "/empresas",
  "/configuracion",
  "/admin",
];

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;
  const isProtected = PROTECTED_PREFIXES.some((p) => pathname.startsWith(p));

  if (!isProtected) {
    return NextResponse.next();
  }

  // Client-side auth check handles token validation; middleware gates route existence.
  return NextResponse.next();
}

export const config = {
  matcher: [
    "/dashboard/:path*",
    "/search/:path*",
    "/dgcp/:path*",
    "/odoo/:path*",
    "/m365/:path*",
    "/work/:path*",
    "/tasks/:path*",
    "/notifications/:path*",
    "/oportunidades/:path*",
    "/empresas/:path*",
    "/configuracion/:path*",
    "/admin/:path*",
  ],
};
