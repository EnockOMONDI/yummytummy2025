#!/usr/bin/env python3
"""
Analyze M-Pesa Callback Redirect Issue
"""

import requests
import json
from datetime import datetime

def trace_callback_redirect_chain():
    """Trace the complete redirect chain for M-Pesa callback URL"""
    print("🔍 M-PESA CALLBACK REDIRECT CHAIN ANALYSIS")
    print("="*60)
    
    callback_url = 'https://www.livegreat.co.ke/mpesa/callback/'
    print(f"🎯 Target URL: {callback_url}")
    print()
    
    current_url = callback_url
    redirect_chain = []
    
    for i in range(10):  # Limit to prevent infinite loops
        print(f"Step {i+1}: Testing {current_url}")
        
        try:
            # Test with GET first to see redirect behavior
            response = requests.get(current_url, allow_redirects=False, timeout=10)
            
            print(f"   Status: {response.status_code}")
            print(f"   Headers: {dict(response.headers)}")
            
            if response.status_code in [301, 302, 307, 308]:
                location = response.headers.get('Location', '')
                print(f"   🔄 Redirects to: {location}")
                
                if location in redirect_chain:
                    print(f"   🚨 REDIRECT LOOP DETECTED!")
                    break
                    
                redirect_chain.append(current_url)
                current_url = location
                
                if not location:
                    print("   ❌ No redirect location provided")
                    break
                    
            elif response.status_code == 405:
                print("   ✅ Reached endpoint (405 Method Not Allowed for GET)")
                break
            elif response.status_code == 200:
                print("   ✅ Reached endpoint (200 OK)")
                break
            else:
                print(f"   ❓ Unexpected status: {response.status_code}")
                break
                
        except Exception as e:
            print(f"   ❌ Error: {e}")
            break
            
        print()
    
    print(f"\n📋 REDIRECT CHAIN SUMMARY:")
    for i, url in enumerate(redirect_chain):
        print(f"   {i+1}. {url}")
    print(f"   Final: {current_url}")
    
    return redirect_chain, current_url

def test_post_redirect_behavior():
    """Test if POST requests are also redirected"""
    print("\n📡 POST REQUEST REDIRECT TEST")
    print("="*40)
    
    callback_url = 'https://www.livegreat.co.ke/mpesa/callback/'
    
    # Sample M-Pesa callback payload
    callback_payload = {
        "Body": {
            "stkCallback": {
                "MerchantRequestID": "TEST-MERCHANT-ID",
                "CheckoutRequestID": "TEST-CHECKOUT-ID",
                "ResultCode": 0,
                "ResultDesc": "Test callback",
                "AccountReference": "TEST-ORDER"
            }
        }
    }
    
    headers = {
        'Content-Type': 'application/json',
        'User-Agent': 'Safaricom-M-Pesa-Callback/1.0'
    }
    
    try:
        # Test POST with allow_redirects=False
        print(f"🔍 Testing POST to: {callback_url}")
        response = requests.post(
            callback_url, 
            json=callback_payload, 
            headers=headers,
            allow_redirects=False,
            timeout=10
        )
        
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.text}")
        
        if response.status_code in [301, 302, 307, 308]:
            location = response.headers.get('Location', '')
            print(f"   🚨 POST REQUEST IS BEING REDIRECTED!")
            print(f"   🔄 Redirect Location: {location}")
            print(f"   📝 This will cause M-Pesa callback failure!")
            
            # Test the redirected URL
            if location:
                print(f"\n🔍 Testing redirected URL: {location}")
                redirect_response = requests.post(
                    location,
                    json=callback_payload,
                    headers=headers,
                    timeout=10
                )
                print(f"   Status: {redirect_response.status_code}")
                print(f"   Response: {redirect_response.text}")
        else:
            print("   ✅ POST request not redirected")
            
    except Exception as e:
        print(f"   ❌ Error testing POST: {e}")

def analyze_redirect_source():
    """Analyze what's causing the redirects"""
    print("\n🔍 REDIRECT SOURCE ANALYSIS")
    print("="*40)
    
    # Test both domains
    test_urls = [
        'https://www.livegreat.co.ke/',
        'https://livegreat.co.ke/',
        'https://www.livegreat.co.ke/mpesa/callback/',
        'https://livegreat.co.ke/mpesa/callback/'
    ]
    
    for url in test_urls:
        print(f"\n🔍 Analyzing: {url}")
        
        try:
            response = requests.get(url, allow_redirects=False, timeout=10)
            
            print(f"   Status: {response.status_code}")
            
            # Check for redirect headers
            if response.status_code in [301, 302, 307, 308]:
                location = response.headers.get('Location', '')
                print(f"   🔄 Location: {location}")
                
                # Analyze redirect headers to identify source
                server = response.headers.get('Server', '')
                cf_ray = response.headers.get('CF-RAY', '')
                x_domain_policy = response.headers.get('x-domain-policy', '')
                
                print(f"   Server: {server}")
                if cf_ray:
                    print(f"   CF-RAY: {cf_ray} (Cloudflare)")
                if x_domain_policy:
                    print(f"   x-domain-policy: {x_domain_policy}")
                
                # Identify redirect source
                if 'cloudflare' in server.lower() or cf_ray:
                    print("   🔍 REDIRECT SOURCE: Cloudflare")
                elif 'render' in server.lower():
                    print("   🔍 REDIRECT SOURCE: Render.com")
                elif x_domain_policy:
                    print("   🔍 REDIRECT SOURCE: Custom domain policy")
                else:
                    print("   🔍 REDIRECT SOURCE: Unknown")
                    
        except Exception as e:
            print(f"   ❌ Error: {e}")

def check_cloudflare_settings():
    """Check if Cloudflare is causing redirects"""
    print("\n☁️ CLOUDFLARE REDIRECT ANALYSIS")
    print("="*40)
    
    print("🔍 Checking for Cloudflare redirect indicators...")
    
    test_url = 'https://www.livegreat.co.ke/'
    
    try:
        response = requests.get(test_url, allow_redirects=False, timeout=10)
        
        # Check Cloudflare headers
        cf_headers = {k: v for k, v in response.headers.items() if k.lower().startswith('cf-')}
        
        if cf_headers:
            print("   ✅ Cloudflare detected:")
            for header, value in cf_headers.items():
                print(f"      {header}: {value}")
                
            # Check for redirect rules
            if response.status_code in [301, 302]:
                print("   🚨 Cloudflare is likely causing redirects")
                print("   📝 Check Cloudflare dashboard for:")
                print("      - Page Rules")
                print("      - Redirect Rules")
                print("      - Transform Rules")
                print("      - Always Use HTTPS setting")
        else:
            print("   ❌ No Cloudflare headers detected")
            
    except Exception as e:
        print(f"   ❌ Error checking Cloudflare: {e}")

if __name__ == "__main__":
    print("🚀 M-PESA CALLBACK REDIRECT DIAGNOSTIC")
    print("="*60)
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Run analysis
    redirect_chain, final_url = trace_callback_redirect_chain()
    test_post_redirect_behavior()
    analyze_redirect_source()
    check_cloudflare_settings()
    
    print("\n" + "="*60)
    print("🎯 CRITICAL FINDINGS:")
    
    if len(redirect_chain) > 0:
        print("❌ M-Pesa callback URL is being redirected!")
        print("📝 This prevents Safaricom from delivering payment callbacks")
        print("🔧 IMMEDIATE ACTION REQUIRED:")
        print("   1. Remove external redirects (Cloudflare/DNS)")
        print("   2. Update M-Pesa callback URL to non-redirected domain")
        print("   3. Test callback accessibility")
    else:
        print("✅ No redirects detected for callback URL")
        
    print("\n📋 Next: Fix redirect configuration and retest M-Pesa payments")
