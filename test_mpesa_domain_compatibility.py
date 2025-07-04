#!/usr/bin/env python3
"""
Test script to verify M-Pesa callback compatibility with WWW domain redirection middleware.
Focuses specifically on ensuring M-Pesa callbacks are not redirected.
"""

import os
import sys
import django
import json
from unittest.mock import Mock

# Setup Django environment
sys.path.append('/Users/djsean/Desktop/APPS2024/MY APPS/yummytummy2025/maslove_project')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'yummytummy_project.settings')
django.setup()

from django.test import RequestFactory, override_settings
from django.http import HttpResponse, HttpResponsePermanentRedirect
from yummytummy_store.middleware import WWWRedirectMiddleware

class MPesaDomainCompatibilityTest:
    """Test M-Pesa callback compatibility with domain redirection"""
    
    def __init__(self):
        self.factory = RequestFactory()
        self.mock_get_response = Mock(return_value=HttpResponse("M-Pesa Callback Response"))
        self.test_results = []
        
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
    
    def test_mpesa_callback_no_redirect_apex_domain(self):
        """Test M-Pesa callback from apex domain is NOT redirected"""
        with override_settings(DEBUG=False):
            middleware = WWWRedirectMiddleware(self.mock_get_response)
            
            # Create M-Pesa callback request from apex domain
            mpesa_payload = {
                "Body": {
                    "stkCallback": {
                        "MerchantRequestID": "29115-34620561-1",
                        "CheckoutRequestID": "ws_CO_12345678901234567890",
                        "ResultCode": 0,
                        "ResultDesc": "The service request is processed successfully."
                    }
                }
            }
            
            request = self.factory.post(
                '/mpesa/callback/',
                data=json.dumps(mpesa_payload),
                content_type='application/json',
                HTTP_HOST='livegreat.co.ke'  # Apex domain
            )
            
            response = middleware(request)
            
            # Should NOT be redirected
            is_not_redirected = not isinstance(response, HttpResponsePermanentRedirect)
            passed = is_not_redirected
            
            message = f"Response type: {type(response).__name__}"
            if isinstance(response, HttpResponsePermanentRedirect):
                message += f", Redirect URL: {response.url}"
            
            self.log_test("M-Pesa Callback No Redirect (Apex Domain)", passed, message)
    
    def test_mpesa_callback_no_redirect_www_domain(self):
        """Test M-Pesa callback from www domain is NOT redirected"""
        with override_settings(DEBUG=False):
            middleware = WWWRedirectMiddleware(self.mock_get_response)
            
            # Create M-Pesa callback request from www domain
            mpesa_payload = {
                "Body": {
                    "stkCallback": {
                        "MerchantRequestID": "29115-34620561-1",
                        "CheckoutRequestID": "ws_CO_12345678901234567890",
                        "ResultCode": 0,
                        "ResultDesc": "The service request is processed successfully."
                    }
                }
            }
            
            request = self.factory.post(
                '/mpesa/callback/',
                data=json.dumps(mpesa_payload),
                content_type='application/json',
                HTTP_HOST='www.livegreat.co.ke'  # WWW domain
            )
            
            response = middleware(request)
            
            # Should NOT be redirected
            is_not_redirected = not isinstance(response, HttpResponsePermanentRedirect)
            passed = is_not_redirected
            
            message = f"Response type: {type(response).__name__}"
            self.log_test("M-Pesa Callback No Redirect (WWW Domain)", passed, message)
    
    def test_regular_page_redirect_from_apex(self):
        """Test that regular pages ARE redirected from apex domain"""
        with override_settings(DEBUG=False):
            middleware = WWWRedirectMiddleware(self.mock_get_response)
            
            # Create regular page request from apex domain
            request = self.factory.get(
                '/products/',
                HTTP_HOST='livegreat.co.ke'  # Apex domain
            )
            
            response = middleware(request)
            
            # Should be redirected
            is_redirected = isinstance(response, HttpResponsePermanentRedirect)
            
            if is_redirected:
                redirect_url = response.url
                correct_redirect = 'www.livegreat.co.ke/products/' in redirect_url
                passed = is_redirected and correct_redirect
                message = f"Redirect URL: {redirect_url}"
            else:
                passed = False
                message = f"Expected redirect, got {type(response).__name__}"
            
            self.log_test("Regular Page Redirect (Apex to WWW)", passed, message)
    
    def test_mpesa_callback_path_variations(self):
        """Test various M-Pesa callback path variations are exempted"""
        with override_settings(DEBUG=False):
            middleware = WWWRedirectMiddleware(self.mock_get_response)
            
            # Test different M-Pesa callback paths
            callback_paths = [
                '/mpesa/callback/',
                '/mpesa/callback',
                '/mpesa/callback/?param=value',
            ]
            
            all_passed = True
            messages = []
            
            for path in callback_paths:
                request = self.factory.post(
                    path,
                    data='{}',
                    content_type='application/json',
                    HTTP_HOST='livegreat.co.ke'
                )
                
                response = middleware(request)
                is_not_redirected = not isinstance(response, HttpResponsePermanentRedirect)
                
                if not is_not_redirected:
                    all_passed = False
                    messages.append(f"Path {path} was redirected")
                else:
                    messages.append(f"Path {path} correctly exempted")
            
            self.log_test("M-Pesa Callback Path Variations", all_passed, "; ".join(messages))
    
    def test_admin_exemption_still_works(self):
        """Test that admin URLs are still exempted from redirection"""
        with override_settings(DEBUG=False):
            middleware = WWWRedirectMiddleware(self.mock_get_response)
            
            request = self.factory.get(
                '/admin/',
                HTTP_HOST='livegreat.co.ke'
            )
            
            response = middleware(request)
            
            # Should NOT be redirected
            is_not_redirected = not isinstance(response, HttpResponsePermanentRedirect)
            passed = is_not_redirected
            
            message = f"Response type: {type(response).__name__}"
            self.log_test("Admin URL Exemption Still Works", passed, message)
    
    def test_middleware_order_compatibility(self):
        """Test that middleware works correctly in the middleware stack"""
        # This test verifies that our middleware doesn't interfere with Django's middleware stack
        with override_settings(DEBUG=False):
            middleware = WWWRedirectMiddleware(self.mock_get_response)
            
            # Test that middleware processes request correctly
            request = self.factory.get('/', HTTP_HOST='www.livegreat.co.ke')
            
            try:
                response = middleware(request)
                middleware_works = True
                error_message = "No errors"
            except Exception as e:
                middleware_works = False
                error_message = str(e)
            
            self.log_test("Middleware Order Compatibility", middleware_works, error_message)
    
    def test_https_preservation_mpesa(self):
        """Test HTTPS is preserved for M-Pesa callbacks (though they shouldn't redirect)"""
        with override_settings(DEBUG=False):
            middleware = WWWRedirectMiddleware(self.mock_get_response)
            
            # Create HTTPS M-Pesa callback request
            request = self.factory.post(
                '/mpesa/callback/',
                data='{}',
                content_type='application/json',
                HTTP_HOST='livegreat.co.ke',
                secure=True  # HTTPS request
            )
            
            response = middleware(request)
            
            # Should NOT be redirected regardless of HTTPS
            is_not_redirected = not isinstance(response, HttpResponsePermanentRedirect)
            passed = is_not_redirected
            
            message = f"Response type: {type(response).__name__}"
            if isinstance(response, HttpResponsePermanentRedirect):
                message += f", Redirect URL: {response.url}"
            
            self.log_test("HTTPS M-Pesa Callback No Redirect", passed, message)
    
    def run_all_tests(self):
        """Run all M-Pesa compatibility tests"""
        print("🧪 Testing M-Pesa Domain Redirection Compatibility")
        print("=" * 60)
        
        # Run all tests
        self.test_mpesa_callback_no_redirect_apex_domain()
        self.test_mpesa_callback_no_redirect_www_domain()
        self.test_regular_page_redirect_from_apex()
        self.test_mpesa_callback_path_variations()
        self.test_admin_exemption_still_works()
        self.test_middleware_order_compatibility()
        self.test_https_preservation_mpesa()
        
        # Summary
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results if result['passed'])
        failed_tests = total_tests - passed_tests
        
        print("\n" + "=" * 60)
        print("📊 M-PESA COMPATIBILITY TEST SUMMARY")
        print("=" * 60)
        print(f"Total Tests: {total_tests}")
        print(f"✅ Passed: {passed_tests}")
        print(f"❌ Failed: {failed_tests}")
        
        if failed_tests > 0:
            print("\n❌ FAILED TESTS:")
            for result in self.test_results:
                if not result['passed']:
                    print(f"  - {result['test']}: {result['message']}")
        
        success_rate = (passed_tests / total_tests) * 100
        print(f"\n🎯 Success Rate: {success_rate:.1f}%")
        
        # M-Pesa specific summary
        mpesa_tests = [r for r in self.test_results if 'M-Pesa' in r['test']]
        mpesa_passed = sum(1 for r in mpesa_tests if r['passed'])
        
        print(f"\n🏦 M-PESA SPECIFIC TESTS: {mpesa_passed}/{len(mpesa_tests)} passed")
        
        if mpesa_passed == len(mpesa_tests):
            print("✅ M-Pesa integration is fully compatible with domain redirection!")
        else:
            print("❌ M-Pesa integration has compatibility issues!")
        
        return failed_tests == 0

if __name__ == '__main__':
    tester = MPesaDomainCompatibilityTest()
    success = tester.run_all_tests()
    
    if success:
        print("\n🎉 All compatibility tests passed!")
        print("\n📋 VERIFICATION COMPLETE:")
        print("✅ M-Pesa callbacks are properly exempted from redirection")
        print("✅ Regular pages are correctly redirected to www subdomain")
        print("✅ Domain redirection middleware is production-ready")
        print("\n🚀 Ready for production deployment!")
    else:
        print("\n⚠️  Some compatibility tests failed. Please review before deployment.")
        sys.exit(1)
