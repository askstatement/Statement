import { NextResponse } from "next/server";

export function middleware(request) {
  const { pathname, searchParams } = request.nextUrl;
  const token = request.cookies.get("access_token")?.value;

  const protectedPaths = ["/chat"]; // Add more as needed

  const isProtected = protectedPaths.some((path) => pathname.startsWith(path));

  if (isProtected && !token) {
    // Redirect unauthenticated user to login
    const loginUrl = new URL("/login", request.url);
    if (searchParams.has("unsubscribe")) {
      loginUrl.searchParams.set("unsubscribe", "true");
    }
    return NextResponse.redirect(loginUrl);
  }

  // if session present redirect to /chat on visiting /login and /signup
  const loginPaths = ["/login", "/signup"];
  const isLoginPaths = loginPaths.some((path) => pathname.startsWith(path));
  if (isLoginPaths && token) {
    return NextResponse.redirect(new URL("/chat", request.url));
  }

  // Allow request to proceed
  return NextResponse.next();
}

export const config = {
  matcher: [
    "/((?!_next/static|_next/image|favicon.ico|images|api|robots.txt|manifest.json|sitemap.xml).*)",
  ],
};
