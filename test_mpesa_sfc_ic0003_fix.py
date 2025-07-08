#!/usr/bin/env python3
"""
Test script for M-Pesa SFC_IC0003 "Receiver party is invalid" fix

This script demonstrates the corrected STK Push payload structure
for Till Number (CustomerBuyGoodsOnline) configuration.

ERROR ANALYSIS:
- SFC_IC0003: "Receiver party is invalid"
- Root Cause: PartyB was set to BusinessShortCode instead of Till Number
- Solution: PartyB must be set to the actual Till Number (8464160)

CONFIGURATION:
- BusinessShortCode: 6319470 (for API authentication)
- Till Number: 8464160 (for PartyB - receiver of funds)
- TransactionType: CustomerBuyGoodsOnline
"""

import os
import sys
import django
import json
from datetime import datetime

# Setup Django environment
sys.path.append('/Users/djsean/Desktop/APPS2024/MY APPS/yummytummy2025/maslove_project')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'yummytummy_project.settings')
django.setup()

from django.conf import settings
from yummytummy_store.mpesa_service import MPesaService

def print_header(title):
    """Print formatted header"""
    print("\n" + "=" * 60)
    print(f"🔧 {title}")
    print("=" * 60)

def print_section(title):
    """Print formatted section"""
    print(f"\n📋 {title}")
    print("-" * 40)

def demonstrate_error_analysis():
    """Demonstrate the SFC_IC0003 error analysis"""
    print_header("M-PESA SFC_IC0003 ERROR ANALYSIS")
    
    print("🚨 ERROR DETAILS:")
    print("   Code: SFC_IC0003")
    print("   Message: 'Receiver party is invalid'")
    print("   Impact: STK Push succeeds but payment fails")
    print()
    
    print("🔍 ROOT CAUSE ANALYSIS:")
    print("   ❌ BEFORE (Incorrect):")
    print("      PartyB: 6319470 (BusinessShortCode)")
    print("      Result: SFC_IC0003 - Receiver party invalid")
    print()
    print("   ✅ AFTER (Correct):")
    print("      PartyB: 8464160 (Till Number)")
    print("      Result: Payment should succeed")
    print()
    
    print("💡 EXPLANATION:")
    print("   For Till Numbers (CustomerBuyGoodsOnline):")
    print("   - BusinessShortCode (6319470): Used for API authentication")
    print("   - Till Number (8464160): Actual receiver of funds (PartyB)")
    print("   - Customer sees Till Number when making payment")

def show_corrected_payload():
    """Show the corrected STK Push payload"""
    print_header("CORRECTED STK PUSH PAYLOAD")
    
    # Create MPesaService instance
    mpesa_service = MPesaService()
    
    # Sample data
    phone_number = "254726436676"
    amount = 2.0
    order_id = 40
    callback_url = "https://livegreat.co.ke/mpesa/callback/"
    
    # Generate password and timestamp (simulated)
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    password_string = f"{mpesa_service.business_short_code}{mpesa_service.passkey}{timestamp}"
    import base64
    password = base64.b64encode(password_string.encode()).decode()
    
    # Format phone number
    formatted_phone = mpesa_service.format_phone_number(phone_number)
    
    print("📤 CORRECTED STK PUSH PAYLOAD:")
    
    # Show the corrected payload
    corrected_payload = {
        'BusinessShortCode': int(mpesa_service.business_short_code),  # 6319470
        'Password': password,
        'Timestamp': timestamp,
        'TransactionType': 'CustomerBuyGoodsOnline',  # Till Number transaction type
        'Amount': int(float(amount)),  # 2
        'PartyA': formatted_phone,  # 254726436676
        'PartyB': int(mpesa_service.till_number),  # 8464160 (FIXED!)
        'PhoneNumber': formatted_phone,  # 254726436676
        'CallBackURL': callback_url,
        'AccountReference': f'YummyTummy-{order_id}',
        'TransactionDesc': f'Payment for YummyTummy Order #{order_id}'
    }
    
    print(json.dumps(corrected_payload, indent=2))
    
    print_section("KEY CHANGES MADE")
    print("✅ PartyB: Changed from 6319470 → 8464160")
    print("✅ Added MPESA_TILL_NUMBER setting")
    print("✅ Updated MPesaService to use Till Number for PartyB")
    print("✅ Maintained BusinessShortCode for authentication")

def simulate_expected_response():
    """Simulate the expected M-Pesa response after fix"""
    print_header("EXPECTED M-PESA RESPONSE AFTER FIX")
    
    print("📥 EXPECTED STK PUSH RESPONSE:")
    expected_stk_response = {
        "MerchantRequestID": "29115-34620561-1",
        "CheckoutRequestID": "ws_CO_07072025120000123456",
        "ResponseCode": "0",
        "ResponseDescription": "Success. Request accepted for processing",
        "CustomerMessage": "Success. Request accepted for processing"
    }
    print(json.dumps(expected_stk_response, indent=2))
    
    print("\n📥 EXPECTED CALLBACK RESPONSE (Success):")
    expected_callback = {
        "Body": {
            "stkCallback": {
                "MerchantRequestID": "29115-34620561-1",
                "CheckoutRequestID": "ws_CO_07072025120000123456",
                "ResultCode": 0,
                "ResultDesc": "The service request is processed successfully.",
                "CallbackMetadata": {
                    "Item": [
                        {"Name": "Amount", "Value": 2.0},
                        {"Name": "MpesaReceiptNumber", "Value": "NLJ7RT61SV"},
                        {"Name": "TransactionDate", "Value": 20250707120000},
                        {"Name": "PhoneNumber", "Value": 254726436676}
                    ]
                }
            }
        }
    }
    print(json.dumps(expected_callback, indent=2))

def show_configuration_verification():
    """Show configuration verification"""
    print_header("CONFIGURATION VERIFICATION")
    
    print("🔧 DJANGO SETTINGS:")
    print(f"   MPESA_BUSINESS_SHORT_CODE: {getattr(settings, 'MPESA_BUSINESS_SHORT_CODE', 'NOT SET')}")
    print(f"   MPESA_TILL_NUMBER: {getattr(settings, 'MPESA_TILL_NUMBER', 'NOT SET')}")
    print(f"   MPESA_TRANSACTION_TYPE: {getattr(settings, 'MPESA_TRANSACTION_TYPE', 'NOT SET')}")
    print(f"   MPESA_ENVIRONMENT: {getattr(settings, 'MPESA_ENVIRONMENT', 'NOT SET')}")
    
    print("\n🏪 TILL NUMBER CONFIGURATION:")
    print("   Type: Till Number (CustomerBuyGoodsOnline)")
    print("   Business Short Code: 6319470 (API authentication)")
    print("   Till Number: 8464160 (PartyB - receiver)")
    print("   Customer Experience: Enter Till Number only")

def show_testing_steps():
    """Show recommended testing steps"""
    print_header("RECOMMENDED TESTING STEPS")
    
    print("🧪 TESTING PROCEDURE:")
    print()
    print("1. VERIFY CONFIGURATION:")
    print("   ✓ Check MPESA_TILL_NUMBER is set to 8464160")
    print("   ✓ Check MPESA_BUSINESS_SHORT_CODE is 6319470")
    print("   ✓ Check MPESA_TRANSACTION_TYPE is CustomerBuyGoodsOnline")
    print()
    print("2. TEST STK PUSH PAYLOAD:")
    print("   ✓ Verify PartyB uses Till Number (8464160)")
    print("   ✓ Verify BusinessShortCode uses 6319470")
    print("   ✓ Verify TransactionType is CustomerBuyGoodsOnline")
    print()
    print("3. MONITOR PAYMENT FLOW:")
    print("   ✓ STK Push should succeed (ResponseCode: '0')")
    print("   ✓ Customer should receive STK Push prompt")
    print("   ✓ Payment should complete without SFC_IC0003 error")
    print("   ✓ Callback should be received with ResultCode: 0")
    print()
    print("4. VERIFY LOGS:")
    print("   ✓ No 'Receiver party is invalid' errors")
    print("   ✓ Successful payment completion")
    print("   ✓ Order status updated to 'paid'")

def main():
    """Main demonstration function"""
    print("🏪 M-PESA SFC_IC0003 FIX DEMONSTRATION")
    print("Till Number Configuration for YummyTummy")
    
    demonstrate_error_analysis()
    show_corrected_payload()
    simulate_expected_response()
    show_configuration_verification()
    show_testing_steps()
    
    print_header("SUMMARY")
    print("✅ ISSUE: SFC_IC0003 'Receiver party is invalid'")
    print("✅ CAUSE: PartyB was set to BusinessShortCode instead of Till Number")
    print("✅ SOLUTION: Updated PartyB to use Till Number (8464160)")
    print("✅ FILES UPDATED:")
    print("   - yummytummy_store/mpesa_service.py")
    print("   - yummytummy_project/settings.py")
    print("✅ READY FOR TESTING: Deploy and test payment flow")

if __name__ == "__main__":
    main()
