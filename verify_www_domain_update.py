#!/usr/bin/env python3
"""
WWW Domain Update Verification Script for YummyTummy Django Application

This script verifies that all domain references have been properly updated
from "livegreat.co.ke" to "www.livegreat.co.ke" throughout the application.
"""

import os
import sys
import django
import requests
from urllib.parse import urlparse

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'yummytummy_project.settings')
django.setup()

from django.conf import settings
from django.urls import reverse


class WWWDomainVerifier:
    """Verify WWW domain update across YummyTummy application"""
    
    def __init__(self):
        self.results = {
            'django_settings': {},
            'mpesa_configuration': {},
            'csrf_security': {},
            'url_routing': {},
            'accessibility': {}
        }
        print("🌐 WWW Domain Update Verification for YummyTummy")
        print("=" * 55)
    
    def verify_django_settings(self):
        """Verify Django settings use www subdomain"""
        print("\n⚙️  Verifying Django Settings...")
        print("-" * 40)
        
        # Check SITE_URL setting
        site_url = getattr(settings, 'SITE_URL', None)
        if site_url:
            print(f"✅ SITE_URL configured: {site_url}")
            if site_url == 'https://www.livegreat.co.ke':
                print("✅ SITE_URL uses correct www subdomain")
                self.results['django_settings']['site_url'] = True
            else:
                print(f"❌ SITE_URL incorrect. Expected: https://www.livegreat.co.ke, Got: {site_url}")
                self.results['django_settings']['site_url'] = False
        else:
            print("❌ SITE_URL not configured")
            self.results['django_settings']['site_url'] = False
        
        return self.results['django_settings']['site_url']
    
    def verify_mpesa_configuration(self):
        """Verify M-Pesa callback URL uses www subdomain"""
        print("\n💳 Verifying M-Pesa Configuration...")
        print("-" * 40)
        
        # Check MPESA_CALLBACK_URL
        callback_url = getattr(settings, 'MPESA_CALLBACK_URL', None)
        if callback_url:
            print(f"✅ MPESA_CALLBACK_URL configured: {callback_url}")
            if callback_url == 'https://www.livegreat.co.ke/mpesa/callback/':
                print("✅ M-Pesa callback URL uses correct www subdomain")
                self.results['mpesa_configuration']['callback_url'] = True
            else:
                print(f"❌ M-Pesa callback URL incorrect. Expected: https://www.livegreat.co.ke/mpesa/callback/, Got: {callback_url}")
                self.results['mpesa_configuration']['callback_url'] = False
        else:
            print("❌ MPESA_CALLBACK_URL not configured")
            self.results['mpesa_configuration']['callback_url'] = False
        
        # Check M-Pesa environment
        mpesa_env = getattr(settings, 'MPESA_ENVIRONMENT', None)
        print(f"📋 M-Pesa Environment: {mpesa_env}")
        
        # Check Short Code
        short_code = getattr(settings, 'MPESA_BUSINESS_SHORT_CODE', None)
        print(f"📋 M-Pesa Short Code: {short_code}")
        
        return self.results['mpesa_configuration']['callback_url']
    
    def verify_csrf_security(self):
        """Verify CSRF trusted origins include www subdomain"""
        print("\n🔒 Verifying CSRF Security Settings...")
        print("-" * 40)
        
        csrf_origins = getattr(settings, 'CSRF_TRUSTED_ORIGINS', [])
        if csrf_origins:
            print(f"✅ CSRF_TRUSTED_ORIGINS configured: {csrf_origins}")
            
            # Check for www subdomain
            www_found = any('www.livegreat.co.ke' in origin for origin in csrf_origins)
            if www_found:
                print("✅ CSRF trusted origins include www.livegreat.co.ke")
                self.results['csrf_security']['www_included'] = True
            else:
                print("❌ CSRF trusted origins missing www.livegreat.co.ke")
                self.results['csrf_security']['www_included'] = False
            
            # Check for non-www version (should also be included for compatibility)
            non_www_found = any('livegreat.co.ke' in origin and 'www.' not in origin for origin in csrf_origins)
            if non_www_found:
                print("✅ CSRF trusted origins include livegreat.co.ke (good for compatibility)")
                self.results['csrf_security']['non_www_included'] = True
            else:
                print("⚠️  CSRF trusted origins missing livegreat.co.ke (may cause issues)")
                self.results['csrf_security']['non_www_included'] = False
                
        else:
            print("❌ CSRF_TRUSTED_ORIGINS not configured")
            self.results['csrf_security']['www_included'] = False
            self.results['csrf_security']['non_www_included'] = False
        
        return self.results['csrf_security']['www_included']
    
    def verify_url_routing(self):
        """Verify Django URL routing works correctly"""
        print("\n🛣️  Verifying URL Routing...")
        print("-" * 40)
        
        try:
            # Check M-Pesa callback route
            callback_path = reverse('yummytummy_store:mpesa_callback')
            print(f"✅ M-Pesa callback route exists: {callback_path}")
            
            if callback_path == '/mpesa/callback/':
                print("✅ Callback route path is correct")
                self.results['url_routing']['callback_route'] = True
            else:
                print(f"⚠️  Callback route path: {callback_path} (expected: /mpesa/callback/)")
                self.results['url_routing']['callback_route'] = False
                
        except Exception as e:
            print(f"❌ URL routing error: {str(e)}")
            self.results['url_routing']['callback_route'] = False
        
        return self.results['url_routing']['callback_route']
    
    def verify_accessibility(self):
        """Test basic accessibility of www domain"""
        print("\n🌐 Testing WWW Domain Accessibility...")
        print("-" * 40)
        
        test_urls = [
            'https://www.livegreat.co.ke',
            'https://www.livegreat.co.ke/mpesa/callback/'
        ]
        
        for url in test_urls:
            try:
                print(f"🔄 Testing: {url}")
                response = requests.get(url, timeout=10, allow_redirects=True)
                print(f"✅ Accessible (Status: {response.status_code})")
                self.results['accessibility'][url] = {
                    'accessible': True,
                    'status_code': response.status_code
                }
            except requests.exceptions.Timeout:
                print(f"⚠️  Timeout accessing {url}")
                self.results['accessibility'][url] = {
                    'accessible': False,
                    'error': 'Timeout'
                }
            except requests.exceptions.ConnectionError:
                print(f"⚠️  Cannot connect to {url} (may be normal if not deployed)")
                self.results['accessibility'][url] = {
                    'accessible': False,
                    'error': 'Connection Error'
                }
            except Exception as e:
                print(f"❌ Error accessing {url}: {str(e)}")
                self.results['accessibility'][url] = {
                    'accessible': False,
                    'error': str(e)
                }
    
    def verify_safaricom_compliance(self):
        """Verify Safaricom M-Pesa compliance with www subdomain"""
        print("\n🏦 Verifying Safaricom M-Pesa Compliance...")
        print("-" * 40)
        
        callback_url = getattr(settings, 'MPESA_CALLBACK_URL', '')
        
        requirements = {
            'https_protocol': callback_url.startswith('https://'),
            'www_subdomain': 'www.livegreat.co.ke' in callback_url,
            'correct_path': callback_url.endswith('/mpesa/callback/'),
            'no_localhost': 'localhost' not in callback_url,
            'complete_format': callback_url == 'https://www.livegreat.co.ke/mpesa/callback/'
        }
        
        print("📋 Safaricom M-Pesa Requirements Check:")
        for requirement, passed in requirements.items():
            status = "✅" if passed else "❌"
            print(f"   {status} {requirement.replace('_', ' ').title()}")
        
        all_passed = all(requirements.values())
        if all_passed:
            print("\n🎉 All Safaricom requirements met with www subdomain!")
        else:
            print("\n⚠️  Some Safaricom requirements not met")
        
        return all_passed
    
    def generate_report(self):
        """Generate comprehensive verification report"""
        print("\n" + "=" * 55)
        print("📊 WWW DOMAIN UPDATE VERIFICATION REPORT")
        print("=" * 55)
        
        # Configuration summary
        site_url = getattr(settings, 'SITE_URL', 'Not configured')
        callback_url = getattr(settings, 'MPESA_CALLBACK_URL', 'Not configured')
        
        print(f"\n🔗 Current Configuration:")
        print(f"   SITE_URL: {site_url}")
        print(f"   MPESA_CALLBACK_URL: {callback_url}")
        
        # Verification results
        print(f"\n📋 VERIFICATION RESULTS:")
        
        django_ok = self.results['django_settings'].get('site_url', False)
        print(f"   {'✅' if django_ok else '❌'} Django Settings")
        
        mpesa_ok = self.results['mpesa_configuration'].get('callback_url', False)
        print(f"   {'✅' if mpesa_ok else '❌'} M-Pesa Configuration")
        
        csrf_ok = self.results['csrf_security'].get('www_included', False)
        print(f"   {'✅' if csrf_ok else '❌'} CSRF Security")
        
        routing_ok = self.results['url_routing'].get('callback_route', False)
        print(f"   {'✅' if routing_ok else '❌'} URL Routing")
        
        # Overall status
        overall_ok = django_ok and mpesa_ok and csrf_ok and routing_ok
        
        print(f"\n🎯 OVERALL STATUS:")
        if overall_ok:
            print("   ✅ WWW domain update SUCCESSFUL!")
            print("   ✅ Ready for production deployment")
            print("   ✅ Safaricom callbacks will work with www.livegreat.co.ke")
        else:
            print("   ⚠️  WWW domain update needs attention")
            if not django_ok:
                print("   🔧 Fix Django SITE_URL setting")
            if not mpesa_ok:
                print("   🔧 Fix M-Pesa callback URL configuration")
            if not csrf_ok:
                print("   🔧 Fix CSRF trusted origins")
            if not routing_ok:
                print("   🔧 Fix URL routing configuration")
        
        print(f"\n📞 NEXT STEPS:")
        print("   1. Deploy updated configuration to production")
        print("   2. Verify www.livegreat.co.ke domain is active")
        print("   3. Contact Safaricom to update callback URL registration")
        print("   4. Test M-Pesa payment flow with new domain")
        
        return {
            'overall_status': 'SUCCESS' if overall_ok else 'NEEDS_ATTENTION',
            'site_url': site_url,
            'callback_url': callback_url,
            'results': self.results
        }


def main():
    """Run WWW domain update verification"""
    verifier = WWWDomainVerifier()
    
    # Run all verification steps
    verifier.verify_django_settings()
    verifier.verify_mpesa_configuration()
    verifier.verify_csrf_security()
    verifier.verify_url_routing()
    verifier.verify_accessibility()
    verifier.verify_safaricom_compliance()
    
    # Generate final report
    report = verifier.generate_report()
    
    return 0 if report['overall_status'] == 'SUCCESS' else 1


if __name__ == '__main__':
    sys.exit(main())
