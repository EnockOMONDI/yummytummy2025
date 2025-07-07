#!/usr/bin/env python3
"""
Diagnostic script to identify redirect loop issues in WWW domain redirection
"""

import requests
import time

def diagnose_redirect_loop():
    """Diagnose redirect loop issues"""
    
    print("🔍 REDIRECT LOOP DIAGNOSTIC")
    print("=" * 50)
    
    # Test different scenarios
    test_urls = [
        "https://www.livegreat.co.ke",
        "https://www.livegreat.co.ke/",
        "https://livegreat.co.ke",
        "https://livegreat.co.ke/",
    ]
    
    for url in test_urls:
        print(f"\n🧪 Testing: {url}")
        try:
            # Follow redirects manually to see the chain
            current_url = url
            redirect_chain = []
            
            for i in range(10):  # Limit to 10 redirects to avoid infinite loop
                response = requests.get(current_url, allow_redirects=False, timeout=10)
                
                print(f"  Step {i+1}: {response.status_code} - {current_url}")
                
                if response.status_code in [301, 302, 307, 308]:
                    location = response.headers.get('Location', '')
                    print(f"    → Redirects to: {location}")
                    
                    if location in redirect_chain:
                        print(f"    🚨 LOOP DETECTED! Already visited: {location}")
                        break
                    
                    redirect_chain.append(current_url)
                    current_url = location
                    
                    if not location:
                        print("    ❌ No redirect location provided")
                        break
                        
                elif response.status_code == 200:
                    print(f"    ✅ Final destination reached: {current_url}")
                    break
                else:
                    print(f"    ❌ Unexpected status: {response.status_code}")
                    break
            
            print(f"  Redirect chain: {' → '.join(redirect_chain + [current_url])}")
            
        except Exception as e:
            print(f"  ❌ Error: {str(e)}")

def check_headers():
    """Check response headers for clues"""
    
    print("\n🔍 HEADER ANALYSIS")
    print("=" * 50)
    
    try:
        response = requests.get("https://www.livegreat.co.ke", allow_redirects=False, timeout=10)
        
        print(f"Status Code: {response.status_code}")
        print("Headers:")
        for key, value in response.headers.items():
            if key.lower() in ['location', 'server', 'x-forwarded-proto', 'host']:
                print(f"  {key}: {value}")
                
    except Exception as e:
        print(f"❌ Error getting headers: {str(e)}")

def test_specific_paths():
    """Test specific paths that should work"""
    
    print("\n🧪 SPECIFIC PATH TESTING")
    print("=" * 50)
    
    paths_to_test = [
        "/admin/",
        "/mpesa/callback/",
        "/static/",
    ]
    
    for path in paths_to_test:
        url = f"https://www.livegreat.co.ke{path}"
        print(f"\n🔗 Testing: {url}")
        
        try:
            response = requests.get(url, allow_redirects=False, timeout=10)
            print(f"  Status: {response.status_code}")
            
            if response.status_code in [301, 302, 307, 308]:
                location = response.headers.get('Location', '')
                print(f"  Redirects to: {location}")
            elif response.status_code == 200:
                print(f"  ✅ Loads successfully")
            else:
                print(f"  Status indicates: {response.reason}")
                
        except Exception as e:
            print(f"  ❌ Error: {str(e)}")

if __name__ == '__main__':
    diagnose_redirect_loop()
    check_headers()
    test_specific_paths()
    
    print("\n" + "=" * 50)
    print("🔧 LIKELY CAUSES & SOLUTIONS")
    print("=" * 50)
    print("1. 🔄 Render.com force HTTPS redirect conflicting with middleware")
    print("2. 🌐 ALLOWED_HOSTS configuration issue")
    print("3. ⚙️  Django SECURE_SSL_REDIRECT setting conflict")
    print("4. 🔗 Multiple redirect middlewares active")
    print("\n💡 NEXT STEPS:")
    print("1. Check Render.com logs for specific error messages")
    print("2. Verify ALLOWED_HOSTS includes www.livegreat.co.ke")
    print("3. Check if SECURE_SSL_REDIRECT is causing conflicts")
    print("4. Temporarily disable custom middleware to isolate issue")
