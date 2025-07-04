#!/usr/bin/env python3
"""
Comprehensive test script for WWW domain redirection middleware.
Tests all aspects of the domain redirection functionality including M-Pesa callback exemptions.
"""

import os
import sys
import django
import time
from unittest.mock import Mock, patch

# Setup Django environment
sys.path.append('/Users/djsean/Desktop/APPS2024/MY APPS/yummytummy2025/maslove_project')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'yummytummy_project.settings')
django.setup()

from django.test import TestCase, RequestFactory, override_settings
from django.http import HttpResponse, HttpResponsePermanentRedirect
from django.conf import settings
from yummytummy_store.middleware import WWWRedirectMiddleware, SecurityHeadersMiddleware

class WWWRedirectionTest:
    """Test suite for WWW domain redirection middleware"""
    
    def __init__(self):
        self.factory = RequestFactory()
        self.test_results = []
        
        # Mock get_response function for middleware testing
        self.mock_get_response = Mock(return_value=HttpResponse("Test Response"))
        
    def log_test(self, test_name, passed, message=""):
        """Log test results"""
        status = "✅ PASS" if passed else "❌ FAIL"
        self.test_results.append({
            'test': test_name,
            'passed': passed,
            'message': message
        })
        print(f"{status}: {test_name}")
        if message:
            print(f"    {message}")
    
    def test_middleware_initialization(self):
        """Test middleware initializes correctly"""
        try:
            middleware = WWWRedirectMiddleware(self.mock_get_response)
            passed = (
                middleware.apex_domain == 'livegreat.co.ke' and
                middleware.www_domain == 'www.livegreat.co.ke' and
                '/mpesa/callback/' in middleware.exempt_paths
            )
            self.log_test("Middleware Initialization", passed,
                         f"Apex: {middleware.apex_domain}, WWW: {middleware.www_domain}")
        except Exception as e:
            self.log_test("Middleware Initialization", False, f"Error: {str(e)}")
    
    def test_development_mode_exemption(self):
        """Test that redirection is skipped in DEBUG mode"""
        with override_settings(DEBUG=True):
            middleware = WWWRedirectMiddleware(self.mock_get_response)
            request = self.factory.get('/', HTTP_HOST='livegreat.co.ke')
            
            response = middleware(request)
            passed = not isinstance(response, HttpResponsePermanentRedirect)
            self.log_test("Development Mode Exemption", passed,
                         f"Response type: {type(response).__name__}")
    
    def test_localhost_exemption(self):
        """Test that localhost requests are not redirected"""
        with override_settings(DEBUG=False):
            middleware = WWWRedirectMiddleware(self.mock_get_response)
            
            # Test localhost
            request = self.factory.get('/', HTTP_HOST='localhost:8000')
            response = middleware(request)
            localhost_passed = not isinstance(response, HttpResponsePermanentRedirect)
            
            # Test 127.0.0.1
            request = self.factory.get('/', HTTP_HOST='127.0.0.1:8000')
            response = middleware(request)
            ip_passed = not isinstance(response, HttpResponsePermanentRedirect)
            
            passed = localhost_passed and ip_passed
            self.log_test("Localhost Exemption", passed,
                         f"Localhost: {localhost_passed}, IP: {ip_passed}")
    
    def test_render_domain_exemption(self):
        """Test that Render.com domains are not redirected"""
        with override_settings(DEBUG=False):
            middleware = WWWRedirectMiddleware(self.mock_get_response)
            request = self.factory.get('/', HTTP_HOST='yummytummy-store.onrender.com')
            
            response = middleware(request)
            passed = not isinstance(response, HttpResponsePermanentRedirect)
            self.log_test("Render Domain Exemption", passed,
                         f"Response type: {type(response).__name__}")
    
    def test_mpesa_callback_exemption(self):
        """Test that M-Pesa callback URLs are not redirected"""
        with override_settings(DEBUG=False):
            middleware = WWWRedirectMiddleware(self.mock_get_response)
            request = self.factory.post('/mpesa/callback/', HTTP_HOST='livegreat.co.ke')
            
            response = middleware(request)
            passed = not isinstance(response, HttpResponsePermanentRedirect)
            self.log_test("M-Pesa Callback Exemption", passed,
                         f"Response type: {type(response).__name__}")
    
    def test_admin_exemption(self):
        """Test that admin URLs are not redirected (optional)"""
        with override_settings(DEBUG=False):
            middleware = WWWRedirectMiddleware(self.mock_get_response)
            request = self.factory.get('/admin/', HTTP_HOST='livegreat.co.ke')
            
            response = middleware(request)
            passed = not isinstance(response, HttpResponsePermanentRedirect)
            self.log_test("Admin URL Exemption", passed,
                         f"Response type: {type(response).__name__}")
    
    def test_apex_domain_redirection(self):
        """Test that apex domain is redirected to www"""
        with override_settings(DEBUG=False):
            middleware = WWWRedirectMiddleware(self.mock_get_response)
            request = self.factory.get('/', HTTP_HOST='livegreat.co.ke')
            
            response = middleware(request)
            is_redirect = isinstance(response, HttpResponsePermanentRedirect)
            
            if is_redirect:
                redirect_url = response.url
                expected_url = 'http://www.livegreat.co.ke/'
                url_correct = redirect_url == expected_url
                passed = is_redirect and url_correct
                message = f"Redirect URL: {redirect_url}, Expected: {expected_url}"
            else:
                passed = False
                message = f"Expected redirect, got {type(response).__name__}"
            
            self.log_test("Apex Domain Redirection", passed, message)
    
    def test_https_redirection(self):
        """Test HTTPS redirection preserves protocol"""
        with override_settings(DEBUG=False):
            middleware = WWWRedirectMiddleware(self.mock_get_response)
            request = self.factory.get('/', HTTP_HOST='livegreat.co.ke', secure=True)
            
            response = middleware(request)
            is_redirect = isinstance(response, HttpResponsePermanentRedirect)
            
            if is_redirect:
                redirect_url = response.url
                https_preserved = redirect_url.startswith('https://')
                www_correct = 'www.livegreat.co.ke' in redirect_url
                passed = https_preserved and www_correct
                message = f"Redirect URL: {redirect_url}"
            else:
                passed = False
                message = f"Expected redirect, got {type(response).__name__}"
            
            self.log_test("HTTPS Protocol Preservation", passed, message)
    
    def test_path_preservation(self):
        """Test that URL paths are preserved during redirection"""
        with override_settings(DEBUG=False):
            middleware = WWWRedirectMiddleware(self.mock_get_response)
            request = self.factory.get('/products/category/spices/', HTTP_HOST='livegreat.co.ke')
            
            response = middleware(request)
            is_redirect = isinstance(response, HttpResponsePermanentRedirect)
            
            if is_redirect:
                redirect_url = response.url
                path_preserved = '/products/category/spices/' in redirect_url
                passed = path_preserved
                message = f"Redirect URL: {redirect_url}"
            else:
                passed = False
                message = f"Expected redirect, got {type(response).__name__}"
            
            self.log_test("URL Path Preservation", passed, message)
    
    def test_query_parameters_preservation(self):
        """Test that query parameters are preserved during redirection"""
        with override_settings(DEBUG=False):
            middleware = WWWRedirectMiddleware(self.mock_get_response)
            request = self.factory.get('/search/?q=turmeric&category=spices', HTTP_HOST='livegreat.co.ke')
            
            response = middleware(request)
            is_redirect = isinstance(response, HttpResponsePermanentRedirect)
            
            if is_redirect:
                redirect_url = response.url
                query_preserved = 'q=turmeric' in redirect_url and 'category=spices' in redirect_url
                passed = query_preserved
                message = f"Redirect URL: {redirect_url}"
            else:
                passed = False
                message = f"Expected redirect, got {type(response).__name__}"
            
            self.log_test("Query Parameters Preservation", passed, message)
    
    def test_www_domain_no_redirection(self):
        """Test that www domain requests are not redirected"""
        with override_settings(DEBUG=False):
            middleware = WWWRedirectMiddleware(self.mock_get_response)
            request = self.factory.get('/', HTTP_HOST='www.livegreat.co.ke')
            
            response = middleware(request)
            passed = not isinstance(response, HttpResponsePermanentRedirect)
            self.log_test("WWW Domain No Redirection", passed,
                         f"Response type: {type(response).__name__}")
    
    def test_security_headers_middleware(self):
        """Test security headers middleware functionality"""
        with override_settings(DEBUG=False, SITE_URL='https://www.livegreat.co.ke'):
            middleware = SecurityHeadersMiddleware(self.mock_get_response)
            request = self.factory.get('/', HTTP_HOST='www.livegreat.co.ke')
            
            response = middleware(request)
            
            has_canonical = 'X-Canonical-Domain' in response
            has_policy = 'X-Domain-Policy' in response
            
            if has_canonical:
                canonical_correct = response['X-Canonical-Domain'] == 'https://www.livegreat.co.ke'
            else:
                canonical_correct = False
            
            if has_policy:
                policy_correct = response['X-Domain-Policy'] == 'www-enforce'
            else:
                policy_correct = False
            
            passed = has_canonical and has_policy and canonical_correct and policy_correct
            message = f"Canonical: {canonical_correct}, Policy: {policy_correct}"
            
            self.log_test("Security Headers Middleware", passed, message)
    
    def test_redirect_status_code(self):
        """Test that redirects use HTTP 301 (permanent redirect)"""
        with override_settings(DEBUG=False):
            middleware = WWWRedirectMiddleware(self.mock_get_response)
            request = self.factory.get('/', HTTP_HOST='livegreat.co.ke')
            
            response = middleware(request)
            is_redirect = isinstance(response, HttpResponsePermanentRedirect)
            
            if is_redirect:
                status_correct = response.status_code == 301
                passed = status_correct
                message = f"Status code: {response.status_code}, Expected: 301"
            else:
                passed = False
                message = f"Expected redirect, got {type(response).__name__}"
            
            self.log_test("HTTP 301 Status Code", passed, message)
    
    def run_all_tests(self):
        """Run all test cases"""
        print("🧪 Testing WWW Domain Redirection Middleware")
        print("=" * 60)
        
        start_time = time.time()
        
        # Run all tests
        self.test_middleware_initialization()
        self.test_development_mode_exemption()
        self.test_localhost_exemption()
        self.test_render_domain_exemption()
        self.test_mpesa_callback_exemption()
        self.test_admin_exemption()
        self.test_apex_domain_redirection()
        self.test_https_redirection()
        self.test_path_preservation()
        self.test_query_parameters_preservation()
        self.test_www_domain_no_redirection()
        self.test_security_headers_middleware()
        self.test_redirect_status_code()
        
        # Summary
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results if result['passed'])
        failed_tests = total_tests - passed_tests
        
        print("\n" + "=" * 60)
        print("📊 TEST SUMMARY")
        print("=" * 60)
        print(f"Total Tests: {total_tests}")
        print(f"✅ Passed: {passed_tests}")
        print(f"❌ Failed: {failed_tests}")
        print(f"⏱️  Duration: {time.time() - start_time:.2f} seconds")
        
        if failed_tests > 0:
            print("\n❌ FAILED TESTS:")
            for result in self.test_results:
                if not result['passed']:
                    print(f"  - {result['test']}: {result['message']}")
        
        success_rate = (passed_tests / total_tests) * 100
        print(f"\n🎯 Success Rate: {success_rate:.1f}%")
        
        return failed_tests == 0

if __name__ == '__main__':
    tester = WWWRedirectionTest()
    success = tester.run_all_tests()
    
    if success:
        print("\n🎉 All tests passed! WWW domain redirection is working correctly.")
        print("\n📋 NEXT STEPS:")
        print("1. Update environment configuration files")
        print("2. Test M-Pesa integration compatibility")
        print("3. Deploy to production and verify")
    else:
        print("\n⚠️  Some tests failed. Please review the implementation.")
        sys.exit(1)
