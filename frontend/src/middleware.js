import { NextResponse } from 'next/server';

export function middleware(request) {
    const { pathname } = request.nextUrl;
    const token = request.cookies.get('access_token')?.value;

    const protectedPaths = ['/chat']; // Add more as needed

    const isProtected = protectedPaths.some((path) =>
      pathname.startsWith(path)
    );

    if (isProtected && !token) {
      // Redirect unauthenticated user to login
      return NextResponse.redirect(new URL('/login', request.url));
    }

    // Allow request to proceed
    return NextResponse.next();
}

export const config = {
    matcher: [
      '/((?!_next/static|_next/image|favicon.ico|images|api|robots.txt|manifest.json|sitemap.xml).*)',
    ],
};