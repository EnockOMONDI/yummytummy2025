#!/usr/bin/env python3
"""
Complete Apex Domain Configuration Verification
Verifies all configuration files are consistent with apex domain approach
"""

import os
import sys
import django
import requests
from datetime import datetime

# Setup Django environment
sys.path.append('/Users/djsean/Desktop/APPS2024/MY APPS/yummytummy2025/maslove_project')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'yummytummy_project.settings')
django.setup()

from django.conf import settings

def verify_django_configuration():
    """Verify Django settings use apex domain"""
    print("⚙️  DJANGO CONFIGURATION VERIFICATION")
    print("="*50)
    
    results = {}
    
    # Check SITE_URL
    site_url = getattr(settings, 'SITE_URL', None)
    expected_site_url = 'https://livegreat.co.ke'
    
    print(f"📋 SITE_URL: {site_url}")
    if site_url == expected_site_url:
        print("   ✅ SITE_URL correctly set to apex domain")
        results['site_url'] = True
    else:
        print(f"   ❌ SITE_URL mismatch. Expected: {expected_site_url}")
        results['site_url'] = False
    
    # Check M-Pesa callback URL
    callback_url = getattr(settings, 'MPESA_CALLBACK_URL', None)
    expected_callback = 'https://livegreat.co.ke/mpesa/callback/'
    
    print(f"📋 MPESA_CALLBACK_URL: {callback_url}")
    if callback_url == expected_callback:
        print("   ✅ M-Pesa callback URL correctly uses apex domain")
        results['callback_url'] = True
    else:
        print(f"   ❌ Callback URL mismatch. Expected: {expected_callback}")
        results['callback_url'] = False
    
    # Check ALLOWED_HOSTS order
    allowed_hosts = getattr(settings, 'ALLOWED_HOSTS', [])
    print(f"📋 ALLOWED_HOSTS: {allowed_hosts}")
    
    if 'livegreat.co.ke' in allowed_hosts and 'www.livegreat.co.ke' in allowed_hosts:
        apex_index = allowed_hosts.index('livegreat.co.ke')
        www_index = allowed_hosts.index('www.livegreat.co.ke')
        
        if apex_index < www_index:
            print("   ✅ Apex domain prioritized in ALLOWED_HOSTS")
            results['allowed_hosts'] = True
        else:
            print("   ⚠️  WWW domain comes before apex domain in ALLOWED_HOSTS")
            results['allowed_hosts'] = False
    else:
        print("   ❌ Missing required domains in ALLOWED_HOSTS")
        results['allowed_hosts'] = False
    
    # Check CSRF_TRUSTED_ORIGINS
    csrf_origins = getattr(settings, 'CSRF_TRUSTED_ORIGINS', [])
    print(f"📋 CSRF_TRUSTED_ORIGINS: {csrf_origins}")
    
    apex_in_csrf = any('livegreat.co.ke' in origin for origin in csrf_origins)
    www_in_csrf = any('www.livegreat.co.ke' in origin for origin in csrf_origins)
    
    if apex_in_csrf and www_in_csrf:
        print("   ✅ Both apex and www domains in CSRF_TRUSTED_ORIGINS")
        results['csrf_origins'] = True
    else:
        print("   ❌ Missing required domains in CSRF_TRUSTED_ORIGINS")
        results['csrf_origins'] = False
    
    print()
    return results

def verify_environment_files():
    """Verify .env and .env.example files"""
    print("📁 ENVIRONMENT FILES VERIFICATION")
    print("="*50)
    
    results = {}
    
    # Check .env file
    try:
        with open('.env', 'r') as f:
            env_content = f.read()
            
        if 'SITE_URL=https://livegreat.co.ke' in env_content:
            print("   ✅ .env file uses apex domain")
            results['env_file'] = True
        else:
            print("   ❌ .env file does not use apex domain")
            results['env_file'] = False
            
    except FileNotFoundError:
        print("   ⚠️  .env file not found")
        results['env_file'] = False
    
    # Check .env.example file
    try:
        with open('.env.example', 'r') as f:
            example_content = f.read()
            
        if 'SITE_URL=https://livegreat.co.ke' in example_content:
            print("   ✅ .env.example file uses apex domain")
            results['env_example'] = True
        else:
            print("   ❌ .env.example file does not use apex domain")
            results['env_example'] = False
            
    except FileNotFoundError:
        print("   ⚠️  .env.example file not found")
        results['env_example'] = False
    
    print()
    return results

def verify_render_configuration():
    """Verify render.yaml configuration"""
    print("☁️  RENDER.COM CONFIGURATION VERIFICATION")
    print("="*50)
    
    results = {}
    
    try:
        with open('render.yaml', 'r') as f:
            render_content = f.read()
        
        # Check SITE_URL in render.yaml
        if 'value: "https://livegreat.co.ke"' in render_content:
            print("   ✅ render.yaml SITE_URL uses apex domain")
            results['render_site_url'] = True
        else:
            print("   ❌ render.yaml SITE_URL does not use apex domain")
            results['render_site_url'] = False
        
        # Check ALLOWED_HOSTS order
        if 'livegreat.co.ke,www.livegreat.co.ke' in render_content:
            print("   ✅ render.yaml ALLOWED_HOSTS prioritizes apex domain")
            results['render_allowed_hosts'] = True
        else:
            print("   ❌ render.yaml ALLOWED_HOSTS does not prioritize apex domain")
            results['render_allowed_hosts'] = False
        
        # Check CSRF_TRUSTED_ORIGINS order
        if 'https://livegreat.co.ke,https://*.onrender.com,https://www.livegreat.co.ke' in render_content:
            print("   ✅ render.yaml CSRF_TRUSTED_ORIGINS prioritizes apex domain")
            results['render_csrf'] = True
        else:
            print("   ❌ render.yaml CSRF_TRUSTED_ORIGINS does not prioritize apex domain")
            results['render_csrf'] = False
            
    except FileNotFoundError:
        print("   ⚠️  render.yaml file not found")
        results = {'render_site_url': False, 'render_allowed_hosts': False, 'render_csrf': False}
    
    print()
    return results

def test_callback_accessibility():
    """Test callback URL accessibility"""
    print("🌐 CALLBACK URL ACCESSIBILITY TEST")
    print("="*50)
    
    callback_url = 'https://livegreat.co.ke/mpesa/callback/'
    
    try:
        # Test GET request (should return 405)
        response = requests.get(callback_url, allow_redirects=False, timeout=10)
        
        print(f"   Testing: {callback_url}")
        print(f"   Status: {response.status_code}")
        
        if response.status_code == 405:
            print("   ✅ Returns 405 (Method Not Allowed) - Expected")
            print("   ✅ No redirects detected")
            
            # Test POST request
            test_payload = {"Body": {"stkCallback": {"ResultCode": 0}}}
            post_response = requests.post(
                callback_url, 
                json=test_payload, 
                allow_redirects=False, 
                timeout=10
            )
            
            print(f"   POST Status: {post_response.status_code}")
            if post_response.status_code == 200:
                print("   ✅ POST request successful")
                return True
            else:
                print("   ❌ POST request failed")
                return False
                
        elif response.status_code in [301, 302, 307, 308]:
            location = response.headers.get('Location', 'No location')
            print(f"   ❌ Redirects to: {location}")
            print("   ❌ This will prevent M-Pesa callbacks")
            return False
        else:
            print(f"   ❓ Unexpected status: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"   ❌ Error testing callback URL: {e}")
        return False

def generate_summary_report(django_results, env_results, render_results, callback_accessible):
    """Generate comprehensive summary report"""
    print("📊 CONFIGURATION SUMMARY REPORT")
    print("="*60)
    
    all_results = {**django_results, **env_results, **render_results}
    total_checks = len(all_results)
    passed_checks = sum(all_results.values())
    
    print(f"📋 CONFIGURATION CHECKS: {passed_checks}/{total_checks} PASSED")
    print()
    
    print("✅ PASSED CHECKS:")
    for check, passed in all_results.items():
        if passed:
            print(f"   ✅ {check.replace('_', ' ').title()}")
    
    print()
    print("❌ FAILED CHECKS:")
    for check, passed in all_results.items():
        if not passed:
            print(f"   ❌ {check.replace('_', ' ').title()}")
    
    print()
    print("🌐 CALLBACK ACCESSIBILITY:")
    if callback_accessible:
        print("   ✅ Callback URL accessible without redirects")
    else:
        print("   ❌ Callback URL accessibility issues")
    
    print()
    
    # Overall status
    config_success = passed_checks == total_checks
    overall_success = config_success and callback_accessible
    
    if overall_success:
        print("🎯 OVERALL STATUS: ✅ SUCCESS")
        print("📝 All configurations updated to apex domain approach")
        print("📝 M-Pesa callback URL should work without redirects")
        print()
        print("🔄 READY FOR:")
        print("   1. Deployment to production")
        print("   2. Safaricom registration verification")
        print("   3. End-to-end M-Pesa payment testing")
    else:
        print("🎯 OVERALL STATUS: ❌ ISSUES DETECTED")
        print("📝 Some configurations still need updates")
        print("📝 Review failed checks above")
    
    return overall_success

if __name__ == "__main__":
    print("🚀 COMPLETE APEX DOMAIN CONFIGURATION VERIFICATION")
    print("="*70)
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Run all verifications
    django_results = verify_django_configuration()
    env_results = verify_environment_files()
    render_results = verify_render_configuration()
    callback_accessible = test_callback_accessibility()
    
    print()
    
    # Generate summary
    success = generate_summary_report(django_results, env_results, render_results, callback_accessible)
    
    print("\n" + "="*70)
    
    if success:
        print("🎉 APEX DOMAIN CONFIGURATION COMPLETE!")
    else:
        print("⚠️  CONFIGURATION NEEDS ATTENTION")
        
    sys.exit(0 if success else 1)
