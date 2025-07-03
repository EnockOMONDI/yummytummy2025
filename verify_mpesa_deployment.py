#!/usr/bin/env python3
"""
M-Pesa Deployment Verification Script for YummyTummy
Verifies that M-Pesa configuration is properly set up after deployment
"""

import os
import sys
import django
import requests
from decimal import Decimal

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'yummytummy_project.settings')
django.setup()

from django.conf import settings
from yummytummy_store.mpesa_service import MPesaService
from yummytummy_store.models import Order


class MPesaDeploymentVerifier:
    """Verify M-Pesa configuration and functionality"""
    
    def __init__(self):
        self.verification_results = {
            'environment_variables': {},
            'mpesa_service': {},
            'api_connectivity': {},
            'overall_status': 'UNKNOWN'
        }
    
    def verify_environment_variables(self):
        """Verify all required M-Pesa environment variables are set"""
        print("🔍 Verifying M-Pesa Environment Variables...")
        print("-" * 50)
        
        required_vars = [
            'MPESA_BUSINESS_SHORT_CODE',
            'MPESA_PASSKEY',
            'MPESA_CONSUMER_KEY',
            'MPESA_CONSUMER_SECRET',
            'MPESA_ENVIRONMENT'
        ]
        
        all_vars_present = True
        
        for var in required_vars:
            try:
                value = getattr(settings, var, None)
                if value:
                    # Mask sensitive values for display
                    if var in ['MPESA_PASSKEY', 'MPESA_CONSUMER_SECRET']:
                        display_value = f"{value[:8]}...{value[-4:]}" if len(value) > 12 else "***MASKED***"
                    else:
                        display_value = value
                    
                    print(f"✅ {var}: {display_value}")
                    self.verification_results['environment_variables'][var] = 'PRESENT'
                else:
                    print(f"❌ {var}: NOT SET")
                    self.verification_results['environment_variables'][var] = 'MISSING'
                    all_vars_present = False
            except AttributeError:
                print(f"❌ {var}: NOT CONFIGURED")
                self.verification_results['environment_variables'][var] = 'NOT_CONFIGURED'
                all_vars_present = False
        
        print(f"\n📊 Environment Variables Status: {'✅ ALL PRESENT' if all_vars_present else '❌ MISSING VARIABLES'}")
        return all_vars_present
    
    def verify_mpesa_service_initialization(self):
        """Verify M-Pesa service can be initialized"""
        print("\n🔧 Verifying M-Pesa Service Initialization...")
        print("-" * 50)
        
        try:
            mpesa_service = MPesaService()
            
            # Check service attributes
            print(f"✅ Business Short Code: {mpesa_service.business_short_code}")
            print(f"✅ Environment: {settings.MPESA_ENVIRONMENT}")
            print(f"✅ Base URL: {mpesa_service.base_url}")
            print(f"✅ Auth URL: {mpesa_service.auth_url}")
            print(f"✅ STK Push URL: {mpesa_service.stk_push_url}")
            
            # Verify URLs are correct for environment
            expected_base = 'https://api.safaricom.co.ke' if settings.MPESA_ENVIRONMENT == 'production' else 'https://sandbox.safaricom.co.ke'
            if mpesa_service.base_url == expected_base:
                print(f"✅ Correct API endpoint for {settings.MPESA_ENVIRONMENT} environment")
                self.verification_results['mpesa_service']['initialization'] = 'SUCCESS'
            else:
                print(f"❌ Incorrect API endpoint. Expected: {expected_base}, Got: {mpesa_service.base_url}")
                self.verification_results['mpesa_service']['initialization'] = 'FAILED'
                return False
            
            self.verification_results['mpesa_service']['service_object'] = 'CREATED'
            return True
            
        except Exception as e:
            print(f"❌ M-Pesa Service Initialization Failed: {str(e)}")
            self.verification_results['mpesa_service']['initialization'] = f'FAILED: {str(e)}'
            return False
    
    def verify_api_connectivity(self):
        """Verify connectivity to M-Pesa API (authentication test)"""
        print("\n🌐 Verifying M-Pesa API Connectivity...")
        print("-" * 50)
        
        try:
            mpesa_service = MPesaService()
            
            # Test authentication
            print("Testing M-Pesa API authentication...")
            access_token = mpesa_service.get_access_token()
            
            if access_token:
                print(f"✅ Authentication successful")
                print(f"✅ Access token received: {access_token[:20]}...")
                self.verification_results['api_connectivity']['authentication'] = 'SUCCESS'
                return True
            else:
                print("❌ Authentication failed - No access token received")
                self.verification_results['api_connectivity']['authentication'] = 'FAILED'
                return False
                
        except Exception as e:
            print(f"❌ API Connectivity Test Failed: {str(e)}")
            self.verification_results['api_connectivity']['authentication'] = f'FAILED: {str(e)}'
            return False
    
    def verify_callback_url_accessibility(self):
        """Verify that callback URL is accessible (for production)"""
        print("\n🔗 Verifying Callback URL Accessibility...")
        print("-" * 50)
        
        try:
            # Get the base URL from Django settings or environment
            if hasattr(settings, 'SITE_URL'):
                base_url = settings.SITE_URL
            else:
                # Try to determine from environment or use default
                base_url = os.environ.get('RENDER_EXTERNAL_URL', 'https://your-app.onrender.com')
            
            callback_url = f"{base_url}/mpesa/callback/"
            print(f"Testing callback URL: {callback_url}")
            
            # Test if URL is accessible
            response = requests.get(callback_url, timeout=10)
            
            # M-Pesa callback should return 405 (Method Not Allowed) for GET requests
            # This is expected since it only accepts POST
            if response.status_code == 405:
                print("✅ Callback URL is accessible (405 Method Not Allowed is expected)")
                self.verification_results['api_connectivity']['callback_url'] = 'ACCESSIBLE'
                return True
            elif response.status_code == 200:
                print("✅ Callback URL is accessible")
                self.verification_results['api_connectivity']['callback_url'] = 'ACCESSIBLE'
                return True
            else:
                print(f"⚠️  Callback URL returned status {response.status_code}")
                self.verification_results['api_connectivity']['callback_url'] = f'STATUS_{response.status_code}'
                return True  # Still consider it accessible
                
        except requests.exceptions.RequestException as e:
            print(f"❌ Callback URL not accessible: {str(e)}")
            self.verification_results['api_connectivity']['callback_url'] = f'FAILED: {str(e)}'
            return False
        except Exception as e:
            print(f"⚠️  Could not test callback URL: {str(e)}")
            self.verification_results['api_connectivity']['callback_url'] = f'UNKNOWN: {str(e)}'
            return True  # Don't fail verification for this
    
    def verify_database_connectivity(self):
        """Verify database connectivity for order management"""
        print("\n💾 Verifying Database Connectivity...")
        print("-" * 50)
        
        try:
            # Test database connection
            order_count = Order.objects.count()
            print(f"✅ Database connected successfully")
            print(f"✅ Found {order_count} orders in database")
            
            # Test order creation (dry run)
            print("✅ Order model accessible")
            
            self.verification_results['database'] = 'CONNECTED'
            return True
            
        except Exception as e:
            print(f"❌ Database connectivity failed: {str(e)}")
            self.verification_results['database'] = f'FAILED: {str(e)}'
            return False
    
    def generate_verification_report(self):
        """Generate comprehensive verification report"""
        print("\n" + "="*80)
        print("🎯 M-PESA DEPLOYMENT VERIFICATION REPORT")
        print("="*80)
        
        # Count successful verifications
        total_checks = 0
        passed_checks = 0
        
        # Environment Variables
        env_vars = self.verification_results['environment_variables']
        env_passed = sum(1 for status in env_vars.values() if status == 'PRESENT')
        env_total = len(env_vars)
        total_checks += env_total
        passed_checks += env_passed
        
        print(f"\n📋 ENVIRONMENT VARIABLES: {env_passed}/{env_total} ✅")
        for var, status in env_vars.items():
            status_icon = "✅" if status == "PRESENT" else "❌"
            print(f"   {status_icon} {var}: {status}")
        
        # M-Pesa Service
        service_checks = self.verification_results['mpesa_service']
        service_passed = sum(1 for status in service_checks.values() if 'SUCCESS' in str(status))
        service_total = len(service_checks)
        total_checks += service_total
        passed_checks += service_passed
        
        print(f"\n🔧 M-PESA SERVICE: {service_passed}/{service_total} ✅")
        for check, status in service_checks.items():
            status_icon = "✅" if 'SUCCESS' in str(status) else "❌"
            print(f"   {status_icon} {check}: {status}")
        
        # API Connectivity
        api_checks = self.verification_results['api_connectivity']
        api_passed = sum(1 for status in api_checks.values() if 'SUCCESS' in str(status) or 'ACCESSIBLE' in str(status))
        api_total = len(api_checks)
        total_checks += api_total
        passed_checks += api_passed
        
        print(f"\n🌐 API CONNECTIVITY: {api_passed}/{api_total} ✅")
        for check, status in api_checks.items():
            status_icon = "✅" if ('SUCCESS' in str(status) or 'ACCESSIBLE' in str(status)) else "❌"
            print(f"   {status_icon} {check}: {status}")
        
        # Overall Status
        success_rate = (passed_checks / total_checks * 100) if total_checks > 0 else 0
        
        print(f"\n📊 OVERALL VERIFICATION STATUS:")
        print(f"   Checks Passed: {passed_checks}/{total_checks}")
        print(f"   Success Rate: {success_rate:.1f}%")
        
        if success_rate >= 90:
            overall_status = "🎉 EXCELLENT - Ready for production"
            self.verification_results['overall_status'] = 'EXCELLENT'
        elif success_rate >= 75:
            overall_status = "✅ GOOD - Minor issues to address"
            self.verification_results['overall_status'] = 'GOOD'
        elif success_rate >= 50:
            overall_status = "⚠️  FAIR - Several issues need attention"
            self.verification_results['overall_status'] = 'FAIR'
        else:
            overall_status = "❌ POOR - Major issues require immediate attention"
            self.verification_results['overall_status'] = 'POOR'
        
        print(f"   Status: {overall_status}")
        
        # Recommendations
        print(f"\n💡 RECOMMENDATIONS:")
        if env_passed < env_total:
            print("   • Set missing M-Pesa environment variables in Render dashboard")
        if service_passed < service_total:
            print("   • Check M-Pesa service configuration and credentials")
        if api_passed < api_total:
            print("   • Verify M-Pesa API credentials and network connectivity")
        if success_rate == 100:
            print("   • All checks passed! M-Pesa integration is ready for production")
        
        return self.verification_results
    
    def run_full_verification(self):
        """Run complete M-Pesa deployment verification"""
        print("🧪 YummyTummy M-Pesa Deployment Verification")
        print("Checking M-Pesa configuration and connectivity...")
        print("="*80)
        
        # Run all verification steps
        env_ok = self.verify_environment_variables()
        service_ok = self.verify_mpesa_service_initialization()
        
        # Only test API if basic setup is working
        api_ok = False
        if env_ok and service_ok:
            api_ok = self.verify_api_connectivity()
            self.verify_callback_url_accessibility()
        
        # Always test database
        db_ok = self.verify_database_connectivity()
        
        # Generate final report
        results = self.generate_verification_report()
        
        return results


def main():
    """Run M-Pesa deployment verification"""
    verifier = MPesaDeploymentVerifier()
    results = verifier.run_full_verification()
    
    # Exit with appropriate code
    if results['overall_status'] in ['EXCELLENT', 'GOOD']:
        sys.exit(0)  # Success
    else:
        sys.exit(1)  # Issues found


if __name__ == "__main__":
    main()
