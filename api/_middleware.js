export default function middleware(request) {
  const url = new URL(request.url);
  
  // Set default security headers for all responses
  const headers = {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type, Authorization',
    'X-Content-Type-Options': 'nosniff',
    'X-Frame-Options': 'DENY',
    'X-XSS-Protection': '1; mode=block',
    'Referrer-Policy': 'strict-origin-when-cross-origin'
  };

  // Handle health check endpoints
  if (url.pathname === '/db-health' || url.pathname.startsWith('/api/health')) {
    return new Response(null, {
      status: 307, // Temporary redirect
      headers: {
        ...headers,
        'Location': '/api/health',
        'Cache-Control': 'no-store, no-cache, must-revalidate, max-age=0'
      }
    });
  }

  // Handle OPTIONS requests for CORS preflight
  if (request.method === 'OPTIONS') {
    return new Response(null, {
      status: 200,
      headers
    });
  }

  // For all other routes, continue with added security headers
  const response = Response.next();
  Object.entries(headers).forEach(([key, value]) => {
    response.headers.set(key, value);
  });
  return response;
}

// Configure middleware to run on all routes
export const config = {
  matcher: ['/:path*']
};

