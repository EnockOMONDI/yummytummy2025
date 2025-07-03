#!/usr/bin/env python
"""
M-Pesa Endpoint Verification Tool for YummyTummy Django Application

This script verifies that the application is using the correct production endpoints
for live M-Pesa transactions and identifies any configuration mismatches.
"""

import os
import sys
import django
from pathlib import Path

# Add the project directory to Python path
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'yummytummy_project.settings')
django.setup()

from django.conf import settings
from yummytummy_store.mpesa_service import MPesaService


def print_header(title):
    """Print formatted section header"""
    print(f"\n{'='*60}")
    print(f"🔍 {title}")
    print(f"{'='*60}")


def print_result(test_name, status, details=""):
    """Print formatted test result"""
    status_icon = "✅" if status == "CORRECT" else "❌" if status == "INCORRECT" else "⚠️"
    print(f"{status_icon} {test_name}: {status}")
    if details:
        print(f"   {details}")


def verify_endpoint_configuration():
    """Verify M-Pesa endpoint configuration"""
    print("🚀 M-PESA ENDPOINT VERIFICATION TOOL")
    print("🎯 YummyTummy Django Application")
    print(f"📅 Current Environment: {getattr(settings, 'MPESA_ENVIRONMENT', 'NOT SET')}")
    
    print_header("CONFIGURATION VERIFICATION")
    
    # Check environment setting
    environment = getattr(settings, 'MPESA_ENVIRONMENT', None)
    if environment == 'production':
        print_result("Environment Setting", "CORRECT", f"MPESA_ENVIRONMENT = {environment}")
    else:
        print_result("Environment Setting", "INCORRECT", f"MPESA_ENVIRONMENT = {environment} (should be 'production')")
    
    # Check base URL
    base_url = getattr(settings, 'MPESA_BASE_URL', None)
    expected_production_base = 'https://api.safaricom.co.ke'
    
    if base_url == expected_production_base:
        print_result("Base URL", "CORRECT", f"MPESA_BASE_URL = {base_url}")
    else:
        print_result("Base URL", "INCORRECT", f"MPESA_BASE_URL = {base_url} (should be {expected_production_base})")
    
    print_header("MPESA SERVICE ENDPOINT VERIFICATION")
    
    # Initialize M-Pesa service and check endpoints
    try:
        mpesa_service = MPesaService()
        
        # Expected production endpoints
        expected_auth_url = "https://api.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials"
        expected_stk_push_url = "https://api.safaricom.co.ke/mpesa/stkpush/v1/processrequest"
        
        # Check OAuth endpoint
        if mpesa_service.auth_url == expected_auth_url:
            print_result("OAuth Endpoint", "CORRECT", f"URL: {mpesa_service.auth_url}")
        else:
            print_result("OAuth Endpoint", "INCORRECT", 
                        f"Current: {mpesa_service.auth_url}\n   Expected: {expected_auth_url}")
        
        # Check STK Push endpoint
        if mpesa_service.stk_push_url == expected_stk_push_url:
            print_result("STK Push Endpoint", "CORRECT", f"URL: {mpesa_service.stk_push_url}")
        else:
            print_result("STK Push Endpoint", "INCORRECT", 
                        f"Current: {mpesa_service.stk_push_url}\n   Expected: {expected_stk_push_url}")
        
        print_header("CREDENTIAL VERIFICATION")
        
        # Check business short code
        business_short_code = mpesa_service.business_short_code
        if business_short_code == '6319470':
            print_result("Business Short Code", "CORRECT", f"Code: {business_short_code}")
        else:
            print_result("Business Short Code", "INCORRECT", f"Code: {business_short_code} (should be 6319470)")
        
        # Check consumer key (production format)
        consumer_key = mpesa_service.consumer_key
        if consumer_key.startswith('p2D6eI01gc'):
            print_result("Consumer Key Format", "CORRECT", f"Key: {consumer_key[:15]}... (production format)")
        else:
            print_result("Consumer Key Format", "WARNING", f"Key: {consumer_key[:15]}... (verify this is production key)")
        
        # Check passkey length
        passkey = mpesa_service.passkey
        if len(passkey) == 64:
            print_result("Passkey Format", "CORRECT", f"Length: {len(passkey)} characters")
        else:
            print_result("Passkey Format", "INCORRECT", f"Length: {len(passkey)} characters (should be 64)")
        
    except Exception as e:
        print_result("M-Pesa Service Initialization", "ERROR", f"Failed to initialize: {str(e)}")
        return False
    
    print_header("ENVIRONMENT VARIABLE CHECK")
    
    # Check .env file values
    env_vars = {
        'MPESA_ENVIRONMENT': os.getenv('MPESA_ENVIRONMENT'),
        'MPESA_BUSINESS_SHORT_CODE': os.getenv('MPESA_BUSINESS_SHORT_CODE'),
        'MPESA_CONSUMER_KEY': os.getenv('MPESA_CONSUMER_KEY'),
        'MPESA_CONSUMER_SECRET': os.getenv('MPESA_CONSUMER_SECRET'),
        'MPESA_PASSKEY': os.getenv('MPESA_PASSKEY')
    }
    
    for var_name, var_value in env_vars.items():
        if var_value:
            if var_name == 'MPESA_ENVIRONMENT':
                status = "CORRECT" if var_value == 'production' else "INCORRECT"
                print_result(f"ENV {var_name}", status, f"Value: {var_value}")
            elif var_name in ['MPESA_CONSUMER_SECRET', 'MPESA_PASSKEY']:
                print_result(f"ENV {var_name}", "SET", f"Length: {len(var_value)} characters")
            else:
                print_result(f"ENV {var_name}", "SET", f"Value: {var_value}")
        else:
            print_result(f"ENV {var_name}", "MISSING", "Not set in environment")
    
    print_header("ENDPOINT COMPARISON SUMMARY")
    
    # Summary table
    print("📊 ENDPOINT COMPARISON:")
    print(f"{'Endpoint':<20} {'Current':<50} {'Expected':<50} {'Status'}")
    print("-" * 130)
    
    current_auth = getattr(mpesa_service, 'auth_url', 'NOT SET')
    current_stk = getattr(mpesa_service, 'stk_push_url', 'NOT SET')
    
    auth_status = "✅ CORRECT" if current_auth == expected_auth_url else "❌ INCORRECT"
    stk_status = "✅ CORRECT" if current_stk == expected_stk_push_url else "❌ INCORRECT"
    
    print(f"{'OAuth':<20} {current_auth:<50} {expected_auth_url:<50} {auth_status}")
    print(f"{'STK Push':<20} {current_stk:<50} {expected_stk_push_url:<50} {stk_status}")
    
    print_header("RECOMMENDATIONS")
    
    # Check if any fixes are needed
    issues_found = []
    
    if environment != 'production':
        issues_found.append("Set MPESA_ENVIRONMENT=production in .env file")
    
    if base_url != expected_production_base:
        issues_found.append("Update MPESA_BASE_URL logic in settings.py")
    
    if current_auth != expected_auth_url:
        issues_found.append("Fix OAuth endpoint configuration")
    
    if current_stk != expected_stk_push_url:
        issues_found.append("Fix STK Push endpoint configuration")
    
    if issues_found:
        print("🔧 ISSUES FOUND - FIXES REQUIRED:")
        for i, issue in enumerate(issues_found, 1):
            print(f"   {i}. {issue}")
        
        print("\n📋 NEXT STEPS:")
        print("   1. Apply the recommended fixes below")
        print("   2. Restart the Django application")
        print("   3. Re-run this verification script")
        print("   4. Test M-Pesa functionality")
        
        return False
    else:
        print("🎉 ALL ENDPOINTS CORRECTLY CONFIGURED!")
        print("   ✅ Production environment is properly set")
        print("   ✅ All API endpoints point to production URLs")
        print("   ✅ Credentials are properly configured")
        
        print("\n🧪 NEXT STEPS:")
        print("   1. Test M-Pesa authentication with production endpoints")
        print("   2. Verify STK Push functionality")
        print("   3. Monitor for any remaining 404.001.03 errors")
        
        return True


def generate_fix_recommendations():
    """Generate specific fix recommendations if issues are found"""
    print_header("CONFIGURATION FIXES")
    
    print("🛠️  If endpoints are incorrect, here are the fixes:")
    
    print("\n1. SETTINGS.PY FIX:")
    print("   Ensure this code is in yummytummy_project/settings.py:")
    print("   ```python")
    print("   MPESA_ENVIRONMENT = config('MPESA_ENVIRONMENT', default='production')")
    print("   MPESA_BASE_URL = 'https://sandbox.safaricom.co.ke' if MPESA_ENVIRONMENT == 'sandbox' else 'https://api.safaricom.co.ke'")
    print("   ```")
    
    print("\n2. .ENV FILE FIX:")
    print("   Ensure this line is in your .env file:")
    print("   ```")
    print("   MPESA_ENVIRONMENT=production")
    print("   ```")
    
    print("\n3. MPESA_SERVICE.PY VERIFICATION:")
    print("   Ensure these lines are in yummytummy_store/mpesa_service.py:")
    print("   ```python")
    print("   self.base_url = settings.MPESA_BASE_URL")
    print("   self.auth_url = f\"{self.base_url}/oauth/v1/generate?grant_type=client_credentials\"")
    print("   self.stk_push_url = f\"{self.base_url}/mpesa/stkpush/v1/processrequest\"")
    print("   ```")


def main():
    """Main function"""
    try:
        config_correct = verify_endpoint_configuration()
        
        if not config_correct:
            generate_fix_recommendations()
        
        return 0 if config_correct else 1
        
    except Exception as e:
        print(f"❌ Verification failed: {str(e)}")
        return 1


if __name__ == '__main__':
    sys.exit(main())
