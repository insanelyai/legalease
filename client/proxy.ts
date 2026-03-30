import { NextRequest, NextResponse } from "next/server"

import { jwtVerify } from "jose"

export async function proxy(req: NextRequest) {
  const token = req.cookies.get("session")?.value

  if (!token) {
    return NextResponse.redirect(new URL("/login", req.url))
  }

  try {
    await jwtVerify(token, new TextEncoder().encode(process.env.JWT_SECRET))
    return NextResponse.next()
  } catch (error) {
    console.error("JWT verification failed:", error)
    return NextResponse.redirect(new URL("/login", req.url))
  }
}
export const config = {
  matcher: [
    "/chat/:path*",
    "/dashboard/:path*",
    "/profile/:path*",
    "/settings/:path*",
  ],
}
