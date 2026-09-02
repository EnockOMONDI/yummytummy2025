"""
Custom middleware for YummyTummy Django application.

This module contains middleware classes that handle various aspects of request processing,
including domain redirection and security enhancements.
"""

import logging
from django.http import HttpResponsePermanentRedirect
from django.conf import settings
from urllib.parse import urlencode

logger = logging.getLogger(__name__)


class WWWRedirectMiddleware:
    """
    Middleware to automatically redirect apex domain to www subdomain.
    
    This middleware ensures that all requests to the apex domain (yummytummy.co.ke)
    are permanently redirected to the www subdomain (www.yummytummy.co.ke) for
    consistent branding and SEO benefits.
    
    Features:
    - HTTP 301 permanent redirects for SEO
    - Preserves URL paths and query parameters
    - Exempts M-Pesa callbacks from redirection
    - Skips redirection in development environment
    - Handles HTTPS/HTTP protocol preservation
    """
    
    def __init__(self, get_response):
        """Initialize the middleware."""
        self.get_response = get_response
        
        # Configuration
        self.apex_domain = 'yummytummy.co.ke'
        self.www_domain = 'www.yummytummy.co.ke'
        
        # Paths that should be exempted from redirection
        self.exempt_paths = [
            '/payments/callback/',  # M-Pesa payment callbacks
            '/mpesa/callback/',  # M-Pesa payment callbacks
            '/admin/',  # Django admin (optional exemption)
        ]
        
        # Development domains that should be exempted
        self.development_domains = [
            'localhost',
            '127.0.0.1',
            'testserver',  # Django test client
        ]
        
        # Render.com domains (deployment platform)
        self.render_domains = [
            '.onrender.com',
        ]
        
        logger.info("WWWRedirectMiddleware initialized")
    
    def __call__(self, request):
        """Process the request and apply redirection if needed."""
        
        # Get the response first (this allows us to modify it if needed)
        response = self.get_response(request)
        
        # Check if redirection is needed
        if self.should_redirect(request):
            redirect_url = self.build_redirect_url(request)
            logger.info(f"Redirecting {request.get_host()}{request.get_full_path()} to {redirect_url}")
            return HttpResponsePermanentRedirect(redirect_url)
        
        return response
    
    def should_redirect(self, request):
        """
        Determine if the request should be redirected to www subdomain.
        
        Args:
            request: Django HttpRequest object
            
        Returns:
            bool: True if redirection is needed, False otherwise
        """
        
        # Skip redirection in DEBUG mode (development)
        if getattr(settings, 'DEBUG', False):
            logger.debug("Skipping WWW redirect in DEBUG mode")
            return False
        
        # Get the current host
        host = request.get_host().lower()
        
        # Remove port number if present (e.g., localhost:8000 -> localhost)
        if ':' in host:
            host = host.split(':')[0]
        
        # Skip redirection for development domains
        if any(dev_domain in host for dev_domain in self.development_domains):
            logger.debug(f"Skipping WWW redirect for development domain: {host}")
            return False
        
        # Skip redirection for Render.com domains
        if any(render_domain in host for render_domain in self.render_domains):
            logger.debug(f"Skipping WWW redirect for Render domain: {host}")
            return False

        # Skip redirection for any .onrender.com subdomain
        if host.endswith('.onrender.com'):
            logger.debug(f"Skipping WWW redirect for Render subdomain: {host}")
            return False
        
        # Skip redirection for exempt paths (e.g., M-Pesa callbacks)
        request_path = request.path

        # Check for exact matches and prefix matches for exempt paths
        for exempt_path in self.exempt_paths:
            # Handle both with and without trailing slash
            exempt_path_no_slash = exempt_path.rstrip('/')
            request_path_no_slash = request_path.rstrip('/')

            if (request_path.startswith(exempt_path) or
                request_path_no_slash == exempt_path_no_slash or
                request_path.startswith(exempt_path_no_slash + '/')):
                logger.debug(f"Skipping WWW redirect for exempt path: {request_path} (matched {exempt_path})")
                return False
        
        # TEMPORARY: Disable middleware to debug redirect loop
        # TODO: Re-enable after fixing external redirect conflicts
        logger.debug(f"WWW redirect middleware temporarily disabled for debugging")
        return False

        # Check if we need to redirect from apex domain to www
        if host == self.apex_domain:
            logger.debug(f"WWW redirect needed: {host} -> {self.www_domain}")
            return True

        # No redirection needed
        return False
    
    def build_redirect_url(self, request):
        """
        Build the redirect URL with www subdomain.
        
        Args:
            request: Django HttpRequest object
            
        Returns:
            str: Complete redirect URL with www subdomain
        """
        
        # Determine protocol (HTTP/HTTPS)
        protocol = 'https' if request.is_secure() else 'http'
        
        # Build the base URL with www subdomain
        redirect_url = f"{protocol}://{self.www_domain}"
        
        # Add the path
        redirect_url += request.path
        
        # Add query parameters if present
        if request.GET:
            query_string = urlencode(request.GET, doseq=True)
            redirect_url += f"?{query_string}"
        
        return redirect_url


class SecurityHeadersMiddleware:
    """
    Middleware to add additional security headers for domain consistency.
    
    This middleware adds security headers that help enforce domain consistency
    and prevent various security attacks related to domain handling.
    """
    
    def __init__(self, get_response):
        """Initialize the middleware."""
        self.get_response = get_response
        logger.info("SecurityHeadersMiddleware initialized")
    
    def __call__(self, request):
        """Process the request and add security headers."""
        
        response = self.get_response(request)
        
        # Add security headers only in production
        if not getattr(settings, 'DEBUG', False):
            # Add canonical domain header
            if hasattr(settings, 'SITE_URL'):
                response['X-Canonical-Domain'] = settings.SITE_URL
            
            # Add domain enforcement header
            response['X-Domain-Policy'] = 'www-enforce'
        
        return response
