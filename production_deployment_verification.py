#!/usr/bin/env python3
"""
Production deployment verification script for WWW domain redirection.
Verifies all configurations are ready for production deployment.
"""

import os
import sys
import django
from pathlib import Path

# Setup Django environment
sys.path.append('/Users/djsean/Desktop/APPS2024/MY APPS/yummytummy2025/maslove_project')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'yummytummy_project.settings')

# Load environment variables from .env file if it exists
env_file = Path('/Users/djsean/Desktop/APPS2024/MY APPS/yummytummy2025/maslove_project/.env')
if env_file.exists():
    with open(env_file) as f:
        for line in f:
            if line.strip() and not line.startswith('#') and '=' in line:
                key, value = line.strip().split('=', 1)
                os.environ[key] = value

django.setup()

from django.conf import settings

class ProductionDeploymentVerification:
    """Verify production deployment readiness"""
    
    def __init__(self):
        self.checks = []
        self.project_root = Path('/Users/djsean/Desktop/APPS2024/MY APPS/yummytummy2025/maslove_project')
        
    def log_check(self, check_name, passed, message="", critical=False):
        """Log verification check results"""
        status = "✅ PASS" if passed else ("🚨 CRITICAL FAIL" if critical else "❌ FAIL")
        self.checks.append({
            'check': check_name,
            'passed': passed,
            'critical': critical,
            'message': message
        })
        print(f"{status}: {check_name}")
        if message:
            print(f"    {message}")
    
    def check_middleware_configuration(self):
        """Verify middleware is properly configured"""
        middleware_list = getattr(settings, 'MIDDLEWARE', [])
        
        # Check if WWW redirect middleware is present
        www_middleware_present = 'yummytummy_store.middleware.WWWRedirectMiddleware' in middleware_list
        
        # Check if security headers middleware is present
        security_middleware_present = 'yummytummy_store.middleware.SecurityHeadersMiddleware' in middleware_list
        
        # Check middleware order (WWW redirect should be early, security headers should be last)
        if www_middleware_present:
            www_index = middleware_list.index('yummytummy_store.middleware.WWWRedirectMiddleware')
            # Should be after SecurityMiddleware and WhiteNoise but before sessions
            proper_order = www_index > 0 and www_index < 5
        else:
            proper_order = False
        
        passed = www_middleware_present and security_middleware_present and proper_order
        message = f"WWW: {www_middleware_present}, Security: {security_middleware_present}, Order: {proper_order}"
        
        self.log_check("Middleware Configuration", passed, message, critical=True)
    
    def check_allowed_hosts_configuration(self):
        """Verify ALLOWED_HOSTS is properly configured"""
        allowed_hosts = getattr(settings, 'ALLOWED_HOSTS', [])
        
        # Check for required domains
        required_domains = ['www.livegreat.co.ke', 'livegreat.co.ke', 'localhost', '127.0.0.1', 'testserver']
        has_required = all(domain in allowed_hosts for domain in required_domains)
        
        # Check for Render.com support
        has_render = any('.onrender.com' in host for host in allowed_hosts)
        
        # Check that wildcard is not used
        no_wildcard = '*' not in allowed_hosts
        
        passed = has_required and has_render and no_wildcard
        message = f"Required domains: {has_required}, Render support: {has_render}, No wildcard: {no_wildcard}"
        
        self.log_check("ALLOWED_HOSTS Configuration", passed, message, critical=True)
    
    def check_csrf_trusted_origins(self):
        """Verify CSRF_TRUSTED_ORIGINS is properly configured"""
        csrf_origins = getattr(settings, 'CSRF_TRUSTED_ORIGINS', [])
        
        # Check for required HTTPS origins
        required_origins = ['https://www.livegreat.co.ke', 'https://livegreat.co.ke']
        has_required = all(origin in csrf_origins for origin in required_origins)

        # Check for Render.com support (including wildcard)
        has_render = any('onrender.com' in origin for origin in csrf_origins)

        # Check WWW is prioritized (should be in the list, order less critical)
        if csrf_origins:
            www_present = 'https://www.livegreat.co.ke' in csrf_origins
        else:
            www_present = False
        
        passed = has_required and has_render and www_present
        message = f"Required origins: {has_required}, Render support: {has_render}, WWW present: {www_present}"
        
        self.log_check("CSRF_TRUSTED_ORIGINS Configuration", passed, message)
    
    def check_middleware_files_exist(self):
        """Verify middleware files exist and are properly structured"""
        middleware_file = self.project_root / 'yummytummy_store' / 'middleware.py'
        
        if middleware_file.exists():
            content = middleware_file.read_text()
            
            # Check for required classes
            has_www_middleware = 'class WWWRedirectMiddleware' in content
            has_security_middleware = 'class SecurityHeadersMiddleware' in content
            
            # Check for required methods
            has_should_redirect = 'def should_redirect' in content
            has_build_redirect_url = 'def build_redirect_url' in content
            
            # Check for M-Pesa exemptions
            has_mpesa_exemption = '/mpesa/callback/' in content
            
            passed = all([has_www_middleware, has_security_middleware, has_should_redirect, 
                         has_build_redirect_url, has_mpesa_exemption])
            message = f"Classes: {has_www_middleware and has_security_middleware}, Methods: {has_should_redirect and has_build_redirect_url}, M-Pesa: {has_mpesa_exemption}"
        else:
            passed = False
            message = "Middleware file does not exist"
        
        self.log_check("Middleware Files Exist", passed, message, critical=True)
    
    def check_environment_files(self):
        """Verify environment configuration files are updated"""
        env_example = self.project_root / '.env.example'
        render_yaml = self.project_root / 'render.yaml'
        
        checks = []
        
        # Check .env.example
        if env_example.exists():
            env_content = env_example.read_text()
            has_www_site_url = 'SITE_URL=https://www.livegreat.co.ke' in env_content
            has_proper_allowed_hosts = 'www.livegreat.co.ke,livegreat.co.ke' in env_content
            has_proper_csrf = 'https://www.livegreat.co.ke,https://livegreat.co.ke' in env_content
            
            env_ok = has_www_site_url and has_proper_allowed_hosts and has_proper_csrf
            checks.append(f".env.example: {env_ok}")
        else:
            env_ok = False
            checks.append(".env.example: Missing")
        
        # Check render.yaml
        if render_yaml.exists():
            render_content = render_yaml.read_text()
            has_proper_hosts = 'www.livegreat.co.ke,livegreat.co.ke' in render_content
            
            render_ok = has_proper_hosts
            checks.append(f"render.yaml: {render_ok}")
        else:
            render_ok = False
            checks.append("render.yaml: Missing")
        
        passed = env_ok and render_ok
        message = "; ".join(checks)
        
        self.log_check("Environment Files Updated", passed, message)
    
    def check_site_url_configuration(self):
        """Verify SITE_URL is configured for www subdomain"""
        site_url = getattr(settings, 'SITE_URL', '')
        
        # Should use www subdomain
        uses_www = 'www.livegreat.co.ke' in site_url
        uses_https = site_url.startswith('https://')
        
        passed = uses_www and uses_https
        message = f"SITE_URL: {site_url}, Uses WWW: {uses_www}, Uses HTTPS: {uses_https}"
        
        self.log_check("SITE_URL Configuration", passed, message, critical=True)
    
    def check_production_security_settings(self):
        """Verify production security settings are properly configured"""
        debug_mode = getattr(settings, 'DEBUG', True)
        
        # In production, DEBUG should be False
        debug_ok = not debug_mode
        
        # Check security settings when DEBUG is False
        if not debug_mode:
            secure_ssl_redirect = getattr(settings, 'SECURE_SSL_REDIRECT', False)
            secure_hsts = getattr(settings, 'SECURE_HSTS_SECONDS', 0) > 0
            session_cookie_secure = getattr(settings, 'SESSION_COOKIE_SECURE', False)
            csrf_cookie_secure = getattr(settings, 'CSRF_COOKIE_SECURE', False)
            
            security_ok = secure_ssl_redirect and secure_hsts and session_cookie_secure and csrf_cookie_secure
        else:
            security_ok = True  # Security settings are conditional on DEBUG=False
        
        passed = debug_ok and security_ok
        message = f"DEBUG: {debug_mode}, Security settings: {security_ok}"
        
        self.log_check("Production Security Settings", passed, message)
    
    def check_test_scripts_available(self):
        """Verify test scripts are available for post-deployment verification"""
        test_files = [
            'test_www_domain_redirection.py',
            'test_mpesa_domain_compatibility.py'
        ]
        
        available_tests = []
        for test_file in test_files:
            test_path = self.project_root / test_file
            if test_path.exists():
                available_tests.append(test_file)
        
        passed = len(available_tests) == len(test_files)
        message = f"Available: {', '.join(available_tests)}"
        
        self.log_check("Test Scripts Available", passed, message)
    
    def run_all_checks(self):
        """Run all production deployment verification checks"""
        print("🚀 Production Deployment Verification")
        print("=" * 60)
        
        # Run all checks
        self.check_middleware_configuration()
        self.check_allowed_hosts_configuration()
        self.check_csrf_trusted_origins()
        self.check_middleware_files_exist()
        self.check_environment_files()
        self.check_site_url_configuration()
        self.check_production_security_settings()
        self.check_test_scripts_available()
        
        # Summary
        total_checks = len(self.checks)
        passed_checks = sum(1 for check in self.checks if check['passed'])
        failed_checks = total_checks - passed_checks
        critical_failures = sum(1 for check in self.checks if not check['passed'] and check['critical'])
        
        print("\n" + "=" * 60)
        print("📊 DEPLOYMENT VERIFICATION SUMMARY")
        print("=" * 60)
        print(f"Total Checks: {total_checks}")
        print(f"✅ Passed: {passed_checks}")
        print(f"❌ Failed: {failed_checks}")
        print(f"🚨 Critical Failures: {critical_failures}")
        
        if failed_checks > 0:
            print("\n❌ FAILED CHECKS:")
            for check in self.checks:
                if not check['passed']:
                    status = "🚨 CRITICAL" if check['critical'] else "❌"
                    print(f"  {status} {check['check']}: {check['message']}")
        
        success_rate = (passed_checks / total_checks) * 100
        print(f"\n🎯 Success Rate: {success_rate:.1f}%")
        
        # Deployment readiness assessment
        if critical_failures == 0 and success_rate >= 90:
            print("\n🎉 DEPLOYMENT READY!")
            print("✅ All critical checks passed")
            print("✅ Configuration is production-ready")
            print("\n📋 NEXT STEPS:")
            print("1. Deploy to production (Render.com)")
            print("2. Run post-deployment verification tests")
            print("3. Monitor logs for redirection behavior")
            print("4. Verify M-Pesa callback functionality")
        elif critical_failures == 0:
            print("\n⚠️  DEPLOYMENT READY WITH WARNINGS")
            print("✅ All critical checks passed")
            print("⚠️  Some non-critical issues detected")
            print("📝 Review failed checks before deployment")
        else:
            print("\n🚨 DEPLOYMENT NOT READY")
            print("❌ Critical configuration issues detected")
            print("🛠️  Fix critical issues before deployment")
        
        return critical_failures == 0

if __name__ == '__main__':
    verifier = ProductionDeploymentVerification()
    ready = verifier.run_all_checks()
    
    if not ready:
        print("\n⚠️  Please fix critical issues before proceeding with deployment.")
        sys.exit(1)
    else:
        print("\n🚀 Ready for production deployment!")
