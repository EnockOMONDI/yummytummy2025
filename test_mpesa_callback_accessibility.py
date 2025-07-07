#!/usr/bin/env python3
"""
Test M-Pesa Callback Accessibility and Domain Configuration Impact
"""

import requests
import json
import time
from datetime import datetime

def test_callback_accessibility():
    """Test if M-Pesa callback URL is accessible from external systems"""
    print("🌐 M-PESA CALLBACK ACCESSIBILITY TEST")
    print("="*50)
    
    # Test both domains
    test_urls = [
        'https://www.livegreat.co.ke/mpesa/callback/',
        'https://livegreat.co.ke/mpesa/callback/'
    ]
    
    for url in test_urls:
        print(f"\n🔍 Testing: {url}")
        print("-" * 40)
        
        try:
            # Test GET request (should return 405 Method Not Allowed)
            print("   📡 Testing GET request...")
            get_response = requests.get(url, timeout=10)
            print(f"   Status: {get_response.status_code}")
            print(f"   Headers: {dict(get_response.headers)}")
            
            if get_response.status_code == 405:
                print("   ✅ GET returns 405 (Method Not Allowed) - Expected for POST-only endpoint")
            elif get_response.status_code == 200:
                print("   ⚠️  GET returns 200 - Unexpected for callback endpoint")
            else:
                print(f"   ❌ GET returns {get_response.status_code} - Unexpected")
            
            # Test POST request (simulate M-Pesa callback)
            print("   📡 Testing POST request (simulated M-Pesa callback)...")
            
            # Sample M-Pesa callback payload
            callback_payload = {
                "Body": {
                    "stkCallback": {
                        "MerchantRequestID": "4544-49a4-a9e1-9a79c8cc90be3358831",
                        "CheckoutRequestID": "ws_CO_07072025221539652726436676",
                        "ResultCode": 0,
                        "ResultDesc": "The service request is processed successfully.",
                        "AccountReference": "36",
                        "CallbackMetadata": {
                            "Item": [
                                {
                                    "Name": "Amount",
                                    "Value": 4.0
                                },
                                {
                                    "Name": "MpesaReceiptNumber",
                                    "Value": "TEST123456789"
                                },
                                {
                                    "Name": "TransactionDate",
                                    "Value": 20250707221539
                                },
                                {
                                    "Name": "PhoneNumber",
                                    "Value": 254726436676
                                }
                            ]
                        }
                    }
                }
            }
            
            headers = {
                'Content-Type': 'application/json',
                'User-Agent': 'Safaricom-M-Pesa-Callback/1.0'
            }
            
            post_response = requests.post(
                url, 
                json=callback_payload, 
                headers=headers,
                timeout=10
            )
            
            print(f"   Status: {post_response.status_code}")
            print(f"   Response: {post_response.text}")
            
            if post_response.status_code == 200:
                try:
                    response_json = post_response.json()
                    if response_json.get('ResultCode') == 0:
                        print("   ✅ POST successful with correct M-Pesa response format")
                    else:
                        print("   ⚠️  POST successful but unexpected response format")
                except:
                    print("   ⚠️  POST successful but response is not JSON")
            else:
                print(f"   ❌ POST failed with status {post_response.status_code}")
                
        except requests.exceptions.Timeout:
            print(f"   ❌ Timeout connecting to {url}")
        except requests.exceptions.ConnectionError:
            print(f"   ❌ Connection error to {url}")
        except Exception as e:
            print(f"   ❌ Error testing {url}: {e}")

def test_domain_redirect_behavior():
    """Test if domain redirects affect callback accessibility"""
    print("\n🔄 DOMAIN REDIRECT BEHAVIOR TEST")
    print("="*50)
    
    test_urls = [
        'https://livegreat.co.ke/',
        'https://www.livegreat.co.ke/',
        'https://livegreat.co.ke/mpesa/callback/',
        'https://www.livegreat.co.ke/mpesa/callback/'
    ]
    
    for url in test_urls:
        print(f"\n🔍 Testing redirects for: {url}")
        print("-" * 40)
        
        try:
            # Test with allow_redirects=False to see redirect behavior
            response = requests.get(url, allow_redirects=False, timeout=10)
            
            print(f"   Status: {response.status_code}")
            
            if response.status_code in [301, 302, 307, 308]:
                location = response.headers.get('Location', 'No location header')
                print(f"   🔄 Redirects to: {location}")
                
                # Test if redirect affects callback
                if '/mpesa/callback/' in url:
                    print("   ⚠️  CRITICAL: Callback URL is being redirected!")
                    print("   📝 This could prevent Safaricom from reaching the callback")
            elif response.status_code == 200:
                print("   ✅ No redirect - serves content directly")
            else:
                print(f"   ❓ Unexpected status: {response.status_code}")
                
        except Exception as e:
            print(f"   ❌ Error testing {url}: {e}")

def test_ssl_certificate():
    """Test SSL certificate validity for both domains"""
    print("\n🔒 SSL CERTIFICATE TEST")
    print("="*50)
    
    import ssl
    import socket
    
    domains = ['livegreat.co.ke', 'www.livegreat.co.ke']
    
    for domain in domains:
        print(f"\n🔍 Testing SSL for: {domain}")
        print("-" * 30)
        
        try:
            context = ssl.create_default_context()
            with socket.create_connection((domain, 443), timeout=10) as sock:
                with context.wrap_socket(sock, server_hostname=domain) as ssock:
                    cert = ssock.getpeercert()
                    
                    print(f"   ✅ SSL Certificate Valid")
                    print(f"   Subject: {cert.get('subject', 'Unknown')}")
                    print(f"   Issuer: {cert.get('issuer', 'Unknown')}")
                    print(f"   Valid Until: {cert.get('notAfter', 'Unknown')}")
                    
        except Exception as e:
            print(f"   ❌ SSL Error for {domain}: {e}")

def analyze_callback_failure():
    """Analyze potential causes of callback failure"""
    print("\n🔍 CALLBACK FAILURE ANALYSIS")
    print("="*50)
    
    print("📋 KNOWN FACTS:")
    print("   ✅ STK Push initiated successfully (ResponseCode: 0)")
    print("   ✅ User entered PIN on mobile device")
    print("   ❌ Payment failed: 'mpesa failed cannot complete payment of ksh 4'")
    print("   ❌ Order 36 still in 'processing' status")
    print("   ❌ No M-Pesa receipt number in database")
    print("   ❌ No transaction ID in database")
    print()
    
    print("🎯 POTENTIAL CAUSES:")
    print("   1. 🌐 Callback URL not accessible to Safaricom")
    print("   2. 🔄 Domain redirects interfering with callback")
    print("   3. 🔒 SSL/TLS issues preventing callback delivery")
    print("   4. 🚫 Firewall or security settings blocking Safaricom IPs")
    print("   5. 📱 M-Pesa system timeout or internal error")
    print("   6. 💰 Insufficient funds or account issues")
    print("   7. 🔧 Django callback processing error")
    print()
    
    print("🔍 INVESTIGATION PRIORITIES:")
    print("   1. ✅ COMPLETED: Verify order exists and transaction IDs match")
    print("   2. 🔄 IN PROGRESS: Test callback URL accessibility")
    print("   3. ⏳ PENDING: Check Django application logs")
    print("   4. ⏳ PENDING: Verify M-Pesa API error handling")
    print("   5. ⏳ PENDING: Test callback with real M-Pesa payload")

if __name__ == "__main__":
    print("🚀 M-PESA CALLBACK DIAGNOSTIC SUITE")
    print("="*60)
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Run all tests
    test_callback_accessibility()
    test_domain_redirect_behavior()
    test_ssl_certificate()
    analyze_callback_failure()
    
    print("\n" + "="*60)
    print("🎯 DIAGNOSTIC COMPLETE")
    print("📝 Review results above to identify callback issues")
    print("📋 Next: Check Django application logs for callback attempts")
