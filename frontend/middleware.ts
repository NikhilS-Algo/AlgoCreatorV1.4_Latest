import { NextResponse } from 'next/server'
import type { NextRequest } from 'next/server'

// These are the public pages that anyone can access without being logged in.
const protectedRoutes = ['/dashboard']

export function middleware(request: NextRequest) {
    // Check for a valid token, or other authentication state
    const authToken = request.cookies.get('token')

    const path = request.nextUrl.pathname
    if (protectedRoutes.includes(path) && !authToken) {
        // Redirect to the login page if trying to access a protected route without a token.
        return NextResponse.redirect(new URL('/', request.url))
    }
}

export const config = {
    matcher: ['/((?!api|_next/static|_next/image).*)']
}
