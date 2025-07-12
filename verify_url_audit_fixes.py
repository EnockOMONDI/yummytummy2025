#!/usr/bin/env python3
"""
Comprehensive URL Audit Verification Script
Verifies that all URL references across the YummyTummy Django project use the correct production domain.
"""

import os
import sys
from pathlib import Path
import re

# Setup Django environment first
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'yummytummy_project.settings')

import django
django.setup()

from django.conf import settings
from django.template.loader import render_to_string
from django.test import RequestFactory
from django.contrib.auth.models import User
from yummytummy_store.models import Order, Product, ProductVariant, AutoCreatedAccount
from yummytummy_store.services import OrderTrackingEmailService

class URLAuditVerifier:
    def __init__(self):
        self.project_root = Path(__file__).parent
        self.results = {
            'services_url_generation': {},
            'email_template_urls': {},
            'template_hardcoded_urls': {},
            'settings_configuration': {}
        }
        self.expected_domain = 'livegreat.co.ke'
        self.expected_protocol = 'https'
        
    def run_verification(self):
        """Run complete URL audit verification"""
        print("🔍 COMPREHENSIVE URL AUDIT VERIFICATION")
        print("=" * 60)
        print(f"Expected Domain: {self.expected_domain}")
        print(f"Expected Protocol: {self.expected_protocol}")
        print()
        
        # Test services.py URL generation
        self.verify_services_url_generation()
        
        # Test email template URL generation
        self.verify_email_template_urls()
        
        # Check for hardcoded URLs in templates
        self.verify_template_hardcoded_urls()
        
        # Verify settings configuration
        self.verify_settings_configuration()
        
        # Generate summary report
        self.generate_summary_report()
        
    def verify_services_url_generation(self):
        """Test URL generation in services.py without request context"""
        print("⚙️  SERVICES.PY URL GENERATION VERIFICATION")
        print("-" * 50)
        
        try:
            # Create test user and auto account
            user = User.objects.create_user(
                username='testuser',
                email='test@example.com',
                password='testpass123'
            )
            
            auto_account = AutoCreatedAccount.objects.create(
                user=user,
                first_login_token='test-token-123'
            )
            
            # Test get_first_login_url without request (fallback to settings)
            login_url = OrderTrackingEmailService.get_first_login_url(auto_account, request=None)
            
            print(f"📋 Generated Login URL: {login_url}")
            
            # Verify URL components
            if login_url.startswith(f'{self.expected_protocol}://{self.expected_domain}'):
                print("✅ Login URL uses correct domain and protocol")
                self.results['services_url_generation']['login_url'] = True
            else:
                print(f"❌ Login URL incorrect. Expected: {self.expected_protocol}://{self.expected_domain}")
                self.results['services_url_generation']['login_url'] = False
            
            # Test order confirmation URL generation
            # Create test order
            product = Product.objects.create(
                name='Test Product',
                description='Test Description',
                price=10.00
            )
            
            variant = ProductVariant.objects.create(
                product=product,
                size='250g',
                price=10.00,
                stock_quantity=100
            )
            
            order = Order.objects.create(
                user=user,
                email='test@example.com',
                phone_number='254700000000',
                first_name='Test',
                last_name='User',
                total_amount=10.00,
                status='pending'
            )
            
            # Test send_regular_order_confirmation URL generation
            context = OrderTrackingEmailService._prepare_order_confirmation_context(order, request=None)
            
            if 'login_url' in context:
                order_login_url = context['login_url']
                print(f"📋 Order Confirmation Login URL: {order_login_url}")
                
                if order_login_url.startswith(f'{self.expected_protocol}://{self.expected_domain}'):
                    print("✅ Order confirmation URL uses correct domain and protocol")
                    self.results['services_url_generation']['order_confirmation_url'] = True
                else:
                    print(f"❌ Order confirmation URL incorrect. Expected: {self.expected_protocol}://{self.expected_domain}")
                    self.results['services_url_generation']['order_confirmation_url'] = False
            else:
                print("ℹ️  Order confirmation context doesn't include login_url (user not authenticated)")
                self.results['services_url_generation']['order_confirmation_url'] = True
            
            # Cleanup test data
            auto_account.delete()
            order.delete()
            variant.delete()
            product.delete()
            user.delete()
            
        except Exception as e:
            print(f"❌ Error testing services URL generation: {e}")
            self.results['services_url_generation']['error'] = str(e)
        
        print()
        
    def verify_email_template_urls(self):
        """Verify email templates generate correct URLs"""
        print("📧 EMAIL TEMPLATE URL VERIFICATION")
        print("-" * 50)
        
        email_templates = [
            'yummytummy_store/emails/order_status_update.html',
            'yummytummy_store/emails/payment_confirmation_with_account.html',
            'yummytummy_store/emails/order_confirmation_user.html',
            'yummytummy_store/emails/order_confirmation_with_account.html'
        ]
        
        for template_path in email_templates:
            try:
                template_file = self.project_root / 'yummytummy_store' / 'templates' / template_path
                
                if template_file.exists():
                    content = template_file.read_text()
                    
                    # Check for hardcoded wrong domains
                    wrong_domains = ['yummytummy.com', 'localhost', '127.0.0.1']
                    has_wrong_domain = any(domain in content for domain in wrong_domains)
                    
                    # Check for correct domain
                    has_correct_domain = self.expected_domain in content
                    
                    print(f"📄 {template_path}")
                    if has_wrong_domain:
                        print(f"   ❌ Contains wrong domain references")
                        self.results['email_template_urls'][template_path] = False
                    elif has_correct_domain:
                        print(f"   ✅ Uses correct domain: {self.expected_domain}")
                        self.results['email_template_urls'][template_path] = True
                    else:
                        print(f"   ℹ️  Uses dynamic URLs (no hardcoded domain)")
                        self.results['email_template_urls'][template_path] = True
                else:
                    print(f"📄 {template_path} - File not found")
                    self.results['email_template_urls'][template_path] = False
                    
            except Exception as e:
                print(f"❌ Error checking {template_path}: {e}")
                self.results['email_template_urls'][template_path] = False
        
        print()
        
    def verify_template_hardcoded_urls(self):
        """Search all templates for hardcoded URLs that should be dynamic"""
        print("🔍 TEMPLATE HARDCODED URL SEARCH")
        print("-" * 50)
        
        template_dir = self.project_root / 'yummytummy_store' / 'templates'
        
        # Patterns to search for
        url_patterns = [
            r'https?://localhost',
            r'https?://127\.0\.0\.1',
            r'https?://yummytummy\.com',
            r'https?://www\.livegreat\.co\.ke'  # Should use apex domain
        ]
        
        found_issues = []
        
        for html_file in template_dir.rglob('*.html'):
            try:
                content = html_file.read_text()
                
                for pattern in url_patterns:
                    matches = re.findall(pattern, content, re.IGNORECASE)
                    if matches:
                        relative_path = html_file.relative_to(self.project_root)
                        found_issues.append({
                            'file': str(relative_path),
                            'pattern': pattern,
                            'matches': matches
                        })
                        
            except Exception as e:
                print(f"❌ Error reading {html_file}: {e}")
        
        if found_issues:
            print("❌ Found hardcoded URL issues:")
            for issue in found_issues:
                print(f"   📄 {issue['file']}")
                print(f"      Pattern: {issue['pattern']}")
                print(f"      Matches: {issue['matches']}")
            self.results['template_hardcoded_urls']['issues_found'] = found_issues
        else:
            print("✅ No hardcoded URL issues found in templates")
            self.results['template_hardcoded_urls']['issues_found'] = []
        
        print()
        
    def verify_settings_configuration(self):
        """Verify Django settings are properly configured"""
        print("⚙️  DJANGO SETTINGS VERIFICATION")
        print("-" * 50)
        
        # Check SITE_URL setting
        site_url = getattr(settings, 'SITE_URL', None)
        expected_site_url = f'{self.expected_protocol}://{self.expected_domain}'
        
        print(f"📋 SITE_URL: {site_url}")
        if site_url == expected_site_url:
            print("✅ SITE_URL correctly configured")
            self.results['settings_configuration']['site_url'] = True
        else:
            print(f"❌ SITE_URL mismatch. Expected: {expected_site_url}")
            self.results['settings_configuration']['site_url'] = False
        
        # Check M-Pesa callback URL
        mpesa_callback_url = getattr(settings, 'MPESA_CALLBACK_URL', None)
        expected_callback_url = f'{expected_site_url}/mpesa/callback/'
        
        print(f"📋 MPESA_CALLBACK_URL: {mpesa_callback_url}")
        if mpesa_callback_url == expected_callback_url:
            print("✅ M-Pesa callback URL correctly configured")
            self.results['settings_configuration']['mpesa_callback_url'] = True
        else:
            print(f"❌ M-Pesa callback URL mismatch. Expected: {expected_callback_url}")
            self.results['settings_configuration']['mpesa_callback_url'] = False
        
        print()
        
    def generate_summary_report(self):
        """Generate comprehensive summary report"""
        print("📊 VERIFICATION SUMMARY REPORT")
        print("=" * 60)
        
        total_checks = 0
        passed_checks = 0
        
        # Count results
        for category, checks in self.results.items():
            if isinstance(checks, dict):
                for check_name, result in checks.items():
                    if isinstance(result, bool):
                        total_checks += 1
                        if result:
                            passed_checks += 1
                    elif check_name == 'issues_found' and isinstance(result, list):
                        total_checks += 1
                        if len(result) == 0:
                            passed_checks += 1
        
        success_rate = (passed_checks / total_checks * 100) if total_checks > 0 else 0
        
        print(f"📈 Overall Success Rate: {success_rate:.1f}% ({passed_checks}/{total_checks})")
        print()
        
        # Detailed results
        for category, checks in self.results.items():
            category_name = category.replace('_', ' ').title()
            print(f"🔍 {category_name}:")
            
            if isinstance(checks, dict):
                for check_name, result in checks.items():
                    if isinstance(result, bool):
                        status = "✅ PASS" if result else "❌ FAIL"
                        print(f"   {check_name}: {status}")
                    elif check_name == 'issues_found':
                        if isinstance(result, list):
                            if len(result) == 0:
                                print(f"   {check_name}: ✅ PASS (No issues)")
                            else:
                                print(f"   {check_name}: ❌ FAIL ({len(result)} issues)")
                    elif check_name == 'error':
                        print(f"   Error: ❌ {result}")
            print()
        
        # Final verdict
        if success_rate >= 100:
            print("🎉 ALL URL AUDIT CHECKS PASSED!")
            print("✅ Production domain configuration is correct")
        elif success_rate >= 80:
            print("⚠️  MOSTLY SUCCESSFUL - Minor issues to address")
        else:
            print("❌ SIGNIFICANT ISSUES FOUND - Requires attention")
        
        print()
        print("🔗 Expected Production URLs:")
        print(f"   • Site URL: {self.expected_protocol}://{self.expected_domain}")
        print(f"   • M-Pesa Callback: {self.expected_protocol}://{self.expected_domain}/mpesa/callback/")
        print(f"   • Order Tracking: {self.expected_protocol}://{self.expected_domain}/account/dashboard/")

if __name__ == '__main__':
    verifier = URLAuditVerifier()
    verifier.run_verification()
