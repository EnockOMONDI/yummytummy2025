#!/usr/bin/env python
"""
M-Pesa Authentication Debug Tool

This script specifically debugs M-Pesa authentication issues to understand
why access tokens are being rejected by the STK Push API.
"""

import os
import sys
import django
import requests
import json
import base64
from datetime import datetime
from pathlib import Path

# Add the project directory to Python path
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'yummytummy_project.settings')
django.setup()

from django.conf import settings
from yummytummy_store.mpesa_service import MPesaService


def test_auth_detailed():
    """Test M-Pesa authentication with detailed debugging"""
    print("🔐 M-PESA AUTHENTICATION DETAILED DEBUG")
    print("=" * 50)
    
    # Get configuration
    consumer_key = settings.MPESA_CONSUMER_KEY
    consumer_secret = settings.MPESA_CONSUMER_SECRET
    environment = settings.MPESA_ENVIRONMENT
    base_url = settings.MPESA_BASE_URL
    
    print(f"Environment: {environment}")
    print(f"Base URL: {base_url}")
    print(f"Consumer Key: {consumer_key[:10]}...")
    print(f"Consumer Secret: {consumer_secret[:10]}...")
    
    # Test authentication manually
    print("\n🧪 MANUAL AUTHENTICATION TEST")
    print("-" * 30)
    
    try:
        # Create basic auth header
        credentials = f"{consumer_key}:{consumer_secret}"
        encoded_credentials = base64.b64encode(credentials.encode()).decode()
        
        headers = {
            'Authorization': f'Basic {encoded_credentials}',
            'Content-Type': 'application/json'
        }
        
        auth_url = f"{base_url}/oauth/v1/generate?grant_type=client_credentials"
        print(f"Auth URL: {auth_url}")
        print(f"Headers: {headers}")
        
        response = requests.get(auth_url, headers=headers, timeout=30)
        print(f"Response Status: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")
        print(f"Response Body: {response.text}")
        
        if response.status_code == 200:
            result = response.json()
            access_token = result.get('access_token')
            expires_in = result.get('expires_in')
            
            print(f"✅ Authentication successful!")
            print(f"Access Token: {access_token[:20]}...")
            print(f"Expires In: {expires_in} seconds")
            
            # Test the token with STK Push endpoint
            print("\n🚀 TESTING ACCESS TOKEN WITH STK PUSH")
            print("-" * 40)
            
            test_stk_push_with_token(access_token, base_url)
            
        else:
            print(f"❌ Authentication failed!")
            print(f"Error: {response.text}")
            
    except Exception as e:
        print(f"❌ Authentication error: {str(e)}")


def test_stk_push_with_token(access_token, base_url):
    """Test STK Push with the obtained access token"""
    
    # Generate password and timestamp
    business_short_code = settings.MPESA_BUSINESS_SHORT_CODE
    passkey = settings.MPESA_PASSKEY
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    password_string = f"{business_short_code}{passkey}{timestamp}"
    password = base64.b64encode(password_string.encode()).decode()
    
    print(f"Business Short Code: {business_short_code}")
    print(f"Timestamp: {timestamp}")
    print(f"Password: {password[:20]}...")
    
    # Prepare STK Push request
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }
    
    payload = {
        'BusinessShortCode': int(business_short_code),
        'Password': password,
        'Timestamp': timestamp,
        'TransactionType': 'CustomerPayBillOnline',
        'Amount': 1,
        'PartyA': '254708374149',  # Test number
        'PartyB': int(business_short_code),
        'PhoneNumber': '254708374149',
        'CallBackURL': 'https://webhook.site/test-callback',
        'AccountReference': 'YummyTummy-TEST',
        'TransactionDesc': 'Test Payment'
    }
    
    stk_push_url = f"{base_url}/mpesa/stkpush/v1/processrequest"
    
    print(f"STK Push URL: {stk_push_url}")
    print(f"Headers: {headers}")
    print(f"Payload: {json.dumps(payload, indent=2)}")
    
    try:
        response = requests.post(stk_push_url, headers=headers, json=payload, timeout=30)
        print(f"STK Push Response Status: {response.status_code}")
        print(f"STK Push Response Headers: {dict(response.headers)}")
        print(f"STK Push Response Body: {response.text}")
        
        if response.status_code == 200:
            result = response.json()
            if result.get('ResponseCode') == '0':
                print("✅ STK Push successful!")
            else:
                print(f"❌ STK Push failed: {result}")
        else:
            print(f"❌ STK Push HTTP error: {response.status_code}")
            
    except Exception as e:
        print(f"❌ STK Push error: {str(e)}")


def test_credentials_validation():
    """Test if credentials are valid for the environment"""
    print("\n🔍 CREDENTIALS VALIDATION")
    print("-" * 30)
    
    environment = settings.MPESA_ENVIRONMENT
    consumer_key = settings.MPESA_CONSUMER_KEY
    
    # Check if credentials match environment
    if environment == 'production':
        if consumer_key.startswith('p2D6eI01gc'):
            print("✅ Credentials appear to be production credentials")
        else:
            print("⚠️  Credentials may not match production environment")
    else:
        if consumer_key.startswith('p2D6eI01gc'):
            print("⚠️  Production credentials being used in sandbox environment")
        else:
            print("✅ Credentials appear to be sandbox credentials")
            
    # Check business short code format
    business_short_code = settings.MPESA_BUSINESS_SHORT_CODE
    if business_short_code.isdigit() and len(business_short_code) in [5, 6, 7]:
        print(f"✅ Business short code format looks valid: {business_short_code}")
    else:
        print(f"⚠️  Business short code format may be invalid: {business_short_code}")
        
    # Check passkey format
    passkey = settings.MPESA_PASSKEY
    if len(passkey) == 64:
        print(f"✅ Passkey length looks correct: {len(passkey)} characters")
    else:
        print(f"⚠️  Passkey length may be incorrect: {len(passkey)} characters")


def main():
    """Main function"""
    print("🚀 M-PESA AUTHENTICATION DEBUG TOOL")
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    test_credentials_validation()
    test_auth_detailed()


if __name__ == '__main__':
    main()
