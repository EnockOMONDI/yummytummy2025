#!/usr/bin/env python3
"""
Direct verification of .env file and callback URL accessibility
"""

import os
import requests
from datetime import datetime

def read_env_file():
    """Read .env file directly"""
    print("📁 DIRECT .ENV FILE VERIFICATION")
    print("="*40)
    
    env_path = '.env'
    env_vars = {}
    
    try:
        with open(env_path, 'r') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    env_vars[key] = value
                    
                    if key == 'SITE_URL':
                        print(f"   Line {line_num}: {key}={value}")
        
        return env_vars
        
    except FileNotFoundError:
        print("   ❌ .env file not found")
        return {}
    except Exception as e:
        print(f"   ❌ Error reading .env file: {e}")
        return {}

def verify_callback_url_construction():
    """Verify how callback URL will be constructed"""
    print("\n🔗 CALLBACK URL CONSTRUCTION")
    print("="*40)
    
    env_vars = read_env_file()
    site_url = env_vars.get('SITE_URL', 'Not found')
    
    print(f"   SITE_URL from .env: {site_url}")
    
    if site_url != 'Not found':
        callback_url = f"{site_url}/mpesa/callback/"
        print(f"   Constructed callback URL: {callback_url}")
        
        # Verify this is the apex domain
        if site_url == 'https://livegreat.co.ke':
            print("   ✅ SITE_URL correctly set to apex domain")
            print("   ✅ Callback URL will use apex domain (no redirects)")
        elif site_url == 'https://www.livegreat.co.ke':
            print("   ❌ SITE_URL still using www subdomain")
            print("   ❌ Callback URL will be redirected (causing failures)")
        else:
            print(f"   ❓ Unexpected SITE_URL value: {site_url}")
            
        return callback_url
    else:
        print("   ❌ SITE_URL not found in .env file")
        return None

def test_callback_accessibility(callback_url):
    """Test if the callback URL is accessible without redirects"""
    print(f"\n🌐 CALLBACK ACCESSIBILITY TEST")
    print("="*40)
    
    if not callback_url:
        print("   ❌ No callback URL to test")
        return False
    
    print(f"   Testing: {callback_url}")
    
    try:
        # Test GET request to check for redirects
        response = requests.get(callback_url, allow_redirects=False, timeout=10)
        
        print(f"   Status: {response.status_code}")
        
        if response.status_code == 405:
            print("   ✅ Returns 405 (Method Not Allowed) - Expected for POST-only endpoint")
            print("   ✅ No redirects detected")
            return True
        elif response.status_code in [301, 302, 307, 308]:
            location = response.headers.get('Location', 'No location')
            print(f"   ❌ Redirects to: {location}")
            print("   ❌ This will prevent M-Pesa callbacks from working")
            return False
        else:
            print(f"   ❓ Unexpected status: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"   ❌ Error testing callback URL: {e}")
        return False

def test_post_request(callback_url):
    """Test POST request to callback URL"""
    print(f"\n📡 POST REQUEST TEST")
    print("="*30)
    
    if not callback_url:
        print("   ❌ No callback URL to test")
        return False
    
    # Sample M-Pesa callback payload
    test_payload = {
        "Body": {
            "stkCallback": {
                "MerchantRequestID": "TEST-VERIFICATION",
                "CheckoutRequestID": "TEST-VERIFICATION",
                "ResultCode": 0,
                "ResultDesc": "Configuration test",
                "AccountReference": "CONFIG-TEST"
            }
        }
    }
    
    headers = {
        'Content-Type': 'application/json',
        'User-Agent': 'M-Pesa-Config-Test/1.0'
    }
    
    try:
        response = requests.post(
            callback_url,
            json=test_payload,
            headers=headers,
            allow_redirects=False,
            timeout=10
        )
        
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.text}")
        
        if response.status_code == 200:
            print("   ✅ POST request successful")
            return True
        elif response.status_code in [301, 302, 307, 308]:
            location = response.headers.get('Location', 'No location')
            print(f"   ❌ POST request redirected to: {location}")
            print("   ❌ This will cause M-Pesa callback failures")
            return False
        else:
            print(f"   ❓ Unexpected POST response: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"   ❌ Error testing POST request: {e}")
        return False

if __name__ == "__main__":
    print("🚀 DIRECT CONFIGURATION VERIFICATION")
    print("="*60)
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Read environment variables directly
    env_vars = read_env_file()
    
    # Verify callback URL construction
    callback_url = verify_callback_url_construction()
    
    # Test callback accessibility
    get_success = test_callback_accessibility(callback_url)
    post_success = test_post_request(callback_url)
    
    print("\n🎯 VERIFICATION SUMMARY:")
    print("="*30)
    
    site_url = env_vars.get('SITE_URL', '')
    
    if site_url == 'https://livegreat.co.ke':
        print("✅ .env file correctly updated to apex domain")
        
        if get_success and post_success:
            print("✅ Callback URL accessible without redirects")
            print("✅ Configuration ready for M-Pesa testing")
            print()
            print("🔄 NEXT STEPS:")
            print("   1. Restart Django application to load new config")
            print("   2. Verify Safaricom registration includes apex domain")
            print("   3. Perform end-to-end M-Pesa payment test")
        else:
            print("❌ Callback URL accessibility issues detected")
            print("📝 Check domain configuration and redirects")
    else:
        print("❌ .env file not properly updated")
        print(f"   Current SITE_URL: {site_url}")
        print("   Expected: https://livegreat.co.ke")
        
    print("\n" + "="*60)
