// Middleware to handle public health check endpoint
export default function middleware(request) {
  const url = new URL(request.url);
  
  // Allow health check endpoint to bypass authentication
  if (url.pathname === '/db-health' || url.pathname.startsWith('/api/health')) {
    // Create a new response with appropriate headers
    const response = new Response(null, {
      status: 307, // Temporary redirect
      headers: {
        'Location': '/api/health',
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'GET, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type, Authorization',
        'Cache-Control': 'no-store, no-cache, must-revalidate, max-age=0'
      }
    });
    
    return response;
  }
  
  // For all other routes, continue to the application
  return;
}

// Configure middleware to run only on health check routes
export const config = {
  matcher: ['/db-health', '/api/health']
};

