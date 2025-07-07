#!/usr/bin/env python3
"""
Verify Apex Domain Configuration for M-Pesa Callbacks
"""

import os
import sys
import django
from datetime import datetime

# Setup Django environment
sys.path.append('/Users/djsean/Desktop/APPS2024/MY APPS/yummytummy2025/maslove_project')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'yummytummy_project.settings')
django.setup()

from django.conf import settings

def verify_configuration():
    """Verify the updated configuration"""
    print("🔍 APEX DOMAIN CONFIGURATION VERIFICATION")
    print("="*50)
    
    print("📋 CURRENT CONFIGURATION:")
    print(f"   SITE_URL: {settings.SITE_URL}")
    print(f"   MPESA_CALLBACK_URL: {settings.MPESA_CALLBACK_URL}")
    print(f"   MPESA_ENVIRONMENT: {settings.MPESA_ENVIRONMENT}")
    print(f"   MPESA_BUSINESS_SHORT_CODE: {settings.MPESA_BUSINESS_SHORT_CODE}")
    print()
    
    # Verify apex domain configuration
    expected_site_url = 'https://livegreat.co.ke'
    expected_callback_url = 'https://livegreat.co.ke/mpesa/callback/'
    
    print("✅ CONFIGURATION VERIFICATION:")
    
    if settings.SITE_URL == expected_site_url:
        print(f"   ✅ SITE_URL correctly set to apex domain: {settings.SITE_URL}")
    else:
        print(f"   ❌ SITE_URL mismatch:")
        print(f"      Expected: {expected_site_url}")
        print(f"      Found: {settings.SITE_URL}")
    
    if settings.MPESA_CALLBACK_URL == expected_callback_url:
        print(f"   ✅ MPESA_CALLBACK_URL correctly set to apex domain: {settings.MPESA_CALLBACK_URL}")
    else:
        print(f"   ❌ MPESA_CALLBACK_URL mismatch:")
        print(f"      Expected: {expected_callback_url}")
        print(f"      Found: {settings.MPESA_CALLBACK_URL}")
    
    print()
    
    # Check other related settings
    print("🔧 RELATED SETTINGS:")
    print(f"   ALLOWED_HOSTS: {settings.ALLOWED_HOSTS}")
    print(f"   CSRF_TRUSTED_ORIGINS: {settings.CSRF_TRUSTED_ORIGINS}")
    print()
    
    return settings.SITE_URL == expected_site_url and settings.MPESA_CALLBACK_URL == expected_callback_url

def check_environment_variables():
    """Check environment variables directly"""
    print("🌍 ENVIRONMENT VARIABLES:")
    print("-" * 30)
    
    from decouple import config
    
    site_url_env = config('SITE_URL', default='Not set')
    print(f"   SITE_URL (from .env): {site_url_env}")
    
    # Check M-Pesa related env vars
    mpesa_vars = [
        'MPESA_BUSINESS_SHORT_CODE',
        'MPESA_PASSKEY',
        'MPESA_CONSUMER_KEY',
        'MPESA_CONSUMER_SECRET',
        'MPESA_ENVIRONMENT'
    ]
    
    for var in mpesa_vars:
        value = config(var, default='Not set')
        if 'SECRET' in var or 'KEY' in var:
            # Mask sensitive values
            masked_value = value[:8] + '...' if len(value) > 8 else 'Set'
            print(f"   {var}: {masked_value}")
        else:
            print(f"   {var}: {value}")
    
    print()

if __name__ == "__main__":
    print("🚀 APEX DOMAIN CONFIGURATION VERIFICATION")
    print("="*60)
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Check environment variables
    check_environment_variables()
    
    # Verify Django configuration
    config_valid = verify_configuration()
    
    print("🎯 VERIFICATION SUMMARY:")
    print("="*30)
    
    if config_valid:
        print("✅ Configuration successfully updated to apex domain")
        print("✅ M-Pesa callback URL now points to https://livegreat.co.ke/mpesa/callback/")
        print("📝 This should eliminate the redirect issue")
        print()
        print("🔄 NEXT STEPS:")
        print("   1. Test callback URL accessibility")
        print("   2. Verify Safaricom registration")
        print("   3. Perform end-to-end M-Pesa payment test")
    else:
        print("❌ Configuration update failed")
        print("📝 Please check .env file and Django settings")
        
    print("\n" + "="*60)
