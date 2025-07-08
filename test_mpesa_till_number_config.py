#!/usr/bin/env python3
"""
M-Pesa Till Number Test Configuration for YummyTummy

CONFIRMED CONFIGURATION:
- Shortcode 6319470 is a Till Number
- Transaction Type: CustomerBuyGoodsOnline
- AccountReference: Not required for Till Numbers

This file provides standardized test data and configuration for all M-Pesa tests
to ensure consistency with the confirmed Till Number setup.
"""

import os
import sys
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'yummytummy_project.settings')
django.setup()

from django.conf import settings

class MPesaTillNumberTestConfig:
    """
    Standardized M-Pesa test configuration for Till Number (CustomerBuyGoodsOnline)
    """
    
    # Confirmed Till Number Configuration
    SHORTCODE = "6319470"  # Business Short Code for API authentication
    TILL_NUMBER = "8464160"  # Actual Till Number for PartyB (receiver)
    TRANSACTION_TYPE = "CustomerBuyGoodsOnline"
    ENVIRONMENT = "production"
    
    # Test Data Templates
    @classmethod
    def get_successful_callback_data(cls, checkout_request_id, merchant_request_id, amount=1000.00):
        """
        Generate successful M-Pesa callback data for Till Number
        
        Note: AccountReference is NOT included as it's not required for Till Numbers
        """
        return {
            "Body": {
                "stkCallback": {
                    "MerchantRequestID": merchant_request_id,
                    "CheckoutRequestID": checkout_request_id,
                    "ResultCode": 0,
                    "ResultDesc": "The service request is processed successfully.",
                    # AccountReference not required for Till Numbers (CustomerBuyGoodsOnline)
                    "CallbackMetadata": {
                        "Item": [
                            {"Name": "Amount", "Value": amount},
                            {"Name": "MpesaReceiptNumber", "Value": f"TEST{checkout_request_id[-6:]}"},
                            {"Name": "TransactionDate", "Value": 20250707120000},
                            {"Name": "PhoneNumber", "Value": 254712345678}
                        ]
                    }
                }
            }
        }
    
    @classmethod
    def get_failed_callback_data(cls, checkout_request_id, merchant_request_id, result_code=1032):
        """
        Generate failed M-Pesa callback data for Till Number
        
        Common failure codes:
        - 1032: Request cancelled by user
        - 2001: Wrong PIN
        - 1025: Request timeout
        """
        return {
            "Body": {
                "stkCallback": {
                    "MerchantRequestID": merchant_request_id,
                    "CheckoutRequestID": checkout_request_id,
                    "ResultCode": result_code,
                    "ResultDesc": cls._get_result_description(result_code)
                    # AccountReference not required for Till Numbers
                }
            }
        }
    
    @classmethod
    def _get_result_description(cls, result_code):
        """Get human-readable description for result codes"""
        descriptions = {
            0: "The service request is processed successfully.",
            1032: "Request cancelled by user",
            2001: "Wrong PIN entered",
            1025: "Request timeout",
            2028: "The request is not permitted according to product assignment"
        }
        return descriptions.get(result_code, f"Unknown error code: {result_code}")
    
    @classmethod
    def get_stk_push_payload(cls, phone_number, amount, order_id):
        """
        Generate STK Push payload for Till Number configuration
        """
        return {
            'BusinessShortCode': cls.SHORTCODE,
            'Password': 'test_password_base64',  # Would be generated in real implementation
            'Timestamp': '20250707120000',
            'TransactionType': cls.TRANSACTION_TYPE,  # CustomerBuyGoodsOnline for Till Number
            'Amount': amount,
            'PartyA': phone_number,
            'PartyB': cls.TILL_NUMBER,  # Use Till Number for PartyB
            'PhoneNumber': phone_number,
            'CallBackURL': f"{settings.SITE_URL}/mpesa/callback/",
            'AccountReference': str(order_id),  # Can be included in STK Push request
            'TransactionDesc': f'Payment for Order {order_id}'
        }
    
    @classmethod
    def verify_configuration(cls):
        """
        Verify that Django settings match Till Number configuration
        """
        issues = []
        
        # Check transaction type setting
        configured_type = getattr(settings, 'MPESA_TRANSACTION_TYPE', None)
        if configured_type != cls.TRANSACTION_TYPE:
            issues.append(f"MPESA_TRANSACTION_TYPE should be '{cls.TRANSACTION_TYPE}', got '{configured_type}'")
        
        # Check shortcode
        configured_shortcode = getattr(settings, 'MPESA_BUSINESS_SHORT_CODE', None)
        if configured_shortcode != cls.SHORTCODE:
            issues.append(f"MPESA_BUSINESS_SHORT_CODE should be '{cls.SHORTCODE}', got '{configured_shortcode}'")

        # Check till number
        configured_till = getattr(settings, 'MPESA_TILL_NUMBER', None)
        if configured_till != cls.TILL_NUMBER:
            issues.append(f"MPESA_TILL_NUMBER should be '{cls.TILL_NUMBER}', got '{configured_till}'")
        
        return issues
    
    @classmethod
    def print_configuration_summary(cls):
        """Print summary of Till Number configuration"""
        print("🏪 M-PESA TILL NUMBER CONFIGURATION")
        print("=" * 50)
        print(f"Business Short Code: {cls.SHORTCODE} (API authentication)")
        print(f"Till Number: {cls.TILL_NUMBER} (PartyB - receiver)")
        print(f"Type: Till Number")
        print(f"Transaction Type: {cls.TRANSACTION_TYPE}")
        print(f"Environment: {cls.ENVIRONMENT}")
        print()
        print("📋 TILL NUMBER CHARACTERISTICS:")
        print("- Customers enter Till Number only (no account number)")
        print("- AccountReference not required in callbacks")
        print("- Used for goods/services payments")
        print("- Simpler customer experience")
        print()
        
        # Verify current configuration
        issues = cls.verify_configuration()
        if issues:
            print("⚠️  CONFIGURATION ISSUES:")
            for issue in issues:
                print(f"   - {issue}")
        else:
            print("✅ Configuration verified - all settings correct")


def main():
    """Demonstrate Till Number test configuration"""
    config = MPesaTillNumberTestConfig()
    config.print_configuration_summary()
    
    print("\n📝 SAMPLE TEST DATA:")
    print("-" * 30)
    
    # Sample successful callback
    success_data = config.get_successful_callback_data(
        "ws_CO_07072025120000123456",
        "29115-34620561-1",
        250.00
    )
    print("Successful Callback Data:")
    import json
    print(json.dumps(success_data, indent=2))
    
    print("\n" + "-" * 30)
    
    # Sample failed callback
    failed_data = config.get_failed_callback_data(
        "ws_CO_07072025120000123456",
        "29115-34620561-1",
        1032
    )
    print("Failed Callback Data:")
    print(json.dumps(failed_data, indent=2))


if __name__ == "__main__":
    main()
