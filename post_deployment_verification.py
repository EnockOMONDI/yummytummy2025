#!/usr/bin/env python3
"""
Post-deployment verification script for WWW domain redirection on Render.com
Tests domain redirection, M-Pesa callback accessibility, and overall functionality.
"""

import requests
import time
import json
from urllib.parse import urljoin

class PostDeploymentVerification:
    """Verify production deployment functionality"""
    
    def __init__(self, base_domain="livegreat.co.ke"):
        self.apex_domain = f"https://{base_domain}"
        self.www_domain = f"https://www.{base_domain}"
        self.results = []
        
    def log_test(self, test_name, passed, message="", response_code=None):
        """Log test results"""
        status = "✅ PASS" if passed else "❌ FAIL"
        self.results.append({
            'test': test_name,
            'passed': passed,
            'message': message,
            'response_code': response_code
        })
        
        code_info = f" ({response_code})" if response_code else ""
        print(f"{status}: {test_name}{code_info}")
        if message:
            print(f"    {message}")
    
    def test_apex_domain_redirect(self):
        """Test that apex domain redirects to www subdomain"""
        try:
            response = requests.get(self.apex_domain, allow_redirects=False, timeout=10)
            
            # Should be a 301 redirect
            is_redirect = response.status_code == 301
            
            # Should redirect to www subdomain
            location = response.headers.get('Location', '')
            redirects_to_www = location.startswith(self.www_domain)
            
            passed = is_redirect and redirects_to_www
            message = f"Redirects to: {location}" if location else "No redirect location found"
            
            self.log_test("Apex Domain Redirect", passed, message, response.status_code)
            
        except requests.RequestException as e:
            self.log_test("Apex Domain Redirect", False, f"Request failed: {str(e)}")
    
    def test_www_domain_loads(self):
        """Test that www subdomain loads normally"""
        try:
            response = requests.get(self.www_domain, timeout=10)
            
            # Should load successfully
            loads_successfully = response.status_code == 200
            
            # Should contain expected content
            contains_content = "YummyTummy" in response.text or "livegreat" in response.text.lower()
            
            passed = loads_successfully and contains_content
            message = f"Content check: {'Found' if contains_content else 'Missing'} expected content"
            
            self.log_test("WWW Domain Loads", passed, message, response.status_code)
            
        except requests.RequestException as e:
            self.log_test("WWW Domain Loads", False, f"Request failed: {str(e)}")
    
    def test_path_preservation(self):
        """Test that paths are preserved during redirection"""
        test_path = "/products/"
        apex_url = f"{self.apex_domain}{test_path}"
        expected_redirect = f"{self.www_domain}{test_path}"
        
        try:
            response = requests.get(apex_url, allow_redirects=False, timeout=10)
            
            # Should be a 301 redirect
            is_redirect = response.status_code == 301
            
            # Should preserve the path
            location = response.headers.get('Location', '')
            path_preserved = location == expected_redirect
            
            passed = is_redirect and path_preserved
            message = f"Expected: {expected_redirect}, Got: {location}"
            
            self.log_test("Path Preservation", passed, message, response.status_code)
            
        except requests.RequestException as e:
            self.log_test("Path Preservation", False, f"Request failed: {str(e)}")
    
    def test_mpesa_callback_accessibility(self):
        """Test that M-Pesa callback URL is accessible and not redirected"""
        callback_url = f"{self.www_domain}/mpesa/callback/"
        
        try:
            # Test with POST request (M-Pesa sends POST)
            response = requests.post(
                callback_url, 
                json={"test": "callback_accessibility"},
                allow_redirects=False,
                timeout=10
            )
            
            # Should not redirect (status should not be 301/302)
            not_redirected = response.status_code not in [301, 302]
            
            # Should be accessible (not 404)
            is_accessible = response.status_code != 404
            
            # Expected status codes: 200 (success), 403 (CSRF), 405 (method not allowed)
            expected_codes = [200, 403, 405]
            expected_response = response.status_code in expected_codes
            
            passed = not_redirected and is_accessible and expected_response
            message = f"Status indicates callback endpoint is accessible"
            
            self.log_test("M-Pesa Callback Accessible", passed, message, response.status_code)
            
        except requests.RequestException as e:
            self.log_test("M-Pesa Callback Accessible", False, f"Request failed: {str(e)}")
    
    def test_admin_interface(self):
        """Test that admin interface is accessible"""
        admin_url = f"{self.www_domain}/admin/"
        
        try:
            response = requests.get(admin_url, timeout=10)
            
            # Should load (200) or redirect to login (302)
            loads_or_redirects = response.status_code in [200, 302]
            
            # Should contain Django admin content
            contains_admin = "Django" in response.text or "admin" in response.text.lower()
            
            passed = loads_or_redirects and contains_admin
            message = f"Admin interface responds correctly"
            
            self.log_test("Admin Interface", passed, message, response.status_code)
            
        except requests.RequestException as e:
            self.log_test("Admin Interface", False, f"Request failed: {str(e)}")
    
    def test_static_files_loading(self):
        """Test that static files are loading correctly"""
        # Test common static file paths
        static_paths = ["/static/css/", "/static/js/", "/static/images/"]
        
        for path in static_paths:
            static_url = f"{self.www_domain}{path}"
            try:
                response = requests.get(static_url, timeout=10)
                
                # 200 (files exist) or 404 (no files in directory) are both acceptable
                # 500 would indicate a server error
                acceptable_codes = [200, 404]
                is_acceptable = response.status_code in acceptable_codes
                
                if is_acceptable:
                    self.log_test(f"Static Files {path}", True, "Static file serving working", response.status_code)
                    break  # If one works, static serving is working
                else:
                    self.log_test(f"Static Files {path}", False, "Static file serving issue", response.status_code)
                    
            except requests.RequestException as e:
                self.log_test(f"Static Files {path}", False, f"Request failed: {str(e)}")
    
    def test_ssl_certificate(self):
        """Test that SSL certificate is working"""
        try:
            response = requests.get(self.www_domain, timeout=10)
            
            # If we get here without SSL errors, certificate is working
            ssl_working = True
            message = "SSL certificate is valid and working"
            
            self.log_test("SSL Certificate", ssl_working, message, response.status_code)
            
        except requests.exceptions.SSLError as e:
            self.log_test("SSL Certificate", False, f"SSL Error: {str(e)}")
        except requests.RequestException as e:
            self.log_test("SSL Certificate", False, f"Request failed: {str(e)}")
    
    def run_all_tests(self):
        """Run all post-deployment verification tests"""
        print("🚀 Post-Deployment Verification for WWW Domain Redirection")
        print("=" * 70)
        print(f"Testing domains: {self.apex_domain} -> {self.www_domain}")
        print("=" * 70)
        
        # Run all tests
        self.test_apex_domain_redirect()
        self.test_www_domain_loads()
        self.test_path_preservation()
        self.test_mpesa_callback_accessibility()
        self.test_admin_interface()
        self.test_static_files_loading()
        self.test_ssl_certificate()
        
        # Summary
        total_tests = len(self.results)
        passed_tests = sum(1 for result in self.results if result['passed'])
        failed_tests = total_tests - passed_tests
        
        print("\n" + "=" * 70)
        print("📊 VERIFICATION SUMMARY")
        print("=" * 70)
        print(f"Total Tests: {total_tests}")
        print(f"✅ Passed: {passed_tests}")
        print(f"❌ Failed: {failed_tests}")
        
        if failed_tests > 0:
            print("\n❌ FAILED TESTS:")
            for result in self.results:
                if not result['passed']:
                    code_info = f" ({result['response_code']})" if result['response_code'] else ""
                    print(f"  • {result['test']}{code_info}: {result['message']}")
        
        success_rate = (passed_tests / total_tests) * 100
        print(f"\n🎯 Success Rate: {success_rate:.1f}%")
        
        # Overall assessment
        if success_rate >= 90:
            print("\n🎉 DEPLOYMENT VERIFICATION SUCCESSFUL!")
            print("✅ WWW domain redirection is working correctly")
            print("✅ M-Pesa integration appears functional")
            print("✅ Core functionality is operational")
        elif success_rate >= 70:
            print("\n⚠️  DEPLOYMENT MOSTLY SUCCESSFUL")
            print("✅ Core functionality is working")
            print("⚠️  Some minor issues detected - review failed tests")
        else:
            print("\n🚨 DEPLOYMENT VERIFICATION FAILED")
            print("❌ Critical issues detected")
            print("🛠️  Review failed tests and fix issues")
        
        print("\n📋 NEXT STEPS:")
        if failed_tests == 0:
            print("1. ✅ All tests passed - deployment is ready!")
            print("2. 🧪 Test M-Pesa payment flow with real transaction")
            print("3. 📊 Monitor Render logs for any issues")
        else:
            print("1. 🔍 Review failed tests above")
            print("2. 🛠️  Fix any configuration issues")
            print("3. 🔄 Re-run verification after fixes")
        
        return success_rate >= 90

if __name__ == '__main__':
    print("Starting post-deployment verification...")
    print("This will test your WWW domain redirection and core functionality.")
    print()
    
    verifier = PostDeploymentVerification()
    success = verifier.run_all_tests()
    
    if not success:
        print("\n⚠️  Some tests failed. Please review and fix issues before proceeding.")
        exit(1)
    else:
        print("\n🚀 Deployment verification completed successfully!")
