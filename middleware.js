export default function middleware(request) {
  const url = new URL(request.url);
  
  // Check if this is a health check route
  if (url.pathname === '/db-health' || 
      url.pathname === '/health' || 
      url.pathname === '/api/health' ||
      url.pathname === '/api/health.py') {
    
    // Allow the request to proceed without authentication
    return new Response(null, {
      status: 200,
      headers: {
        'x-middleware-skip': '1',
        'x-middleware-rewrite': url.pathname === '/db-health' || url.pathname === '/health' 
          ? '/api/health.py' 
          : url.pathname
      }
    });
  }
  
  // For all other routes, proceed with normal processing
  return;
}

export const config = {
  matcher: ['/db-health', '/health', '/api/health', '/api/health.py']
};

