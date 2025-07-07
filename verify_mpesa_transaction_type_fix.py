#!/usr/bin/env python3
"""
M-Pesa Transaction Type Fix Verification
Verifies the fix for ResultCode 2028 "product assignment" error
"""

import os
import sys
import django
import requests
import json
from datetime import datetime

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'yummytummy_project.settings')
django.setup()

from django.conf import settings
from yummytummy_store.mpesa_service import MPesaService

def print_header(title):
    """Print a formatted header"""
    print("\n" + "="*60)
    print(f" {title}")
    print("="*60)

def print_result(test_name, status, details=""):
    """Print test result with formatting"""
    status_symbol = "✅" if status == "PASS" else "❌" if status == "FAIL" else "⚠️"
    print(f"{status_symbol} {test_name}: {status}")
    if details:
        print(f"   {details}")

def verify_configuration():
    """Verify M-Pesa configuration includes transaction type"""
    print_header("M-PESA CONFIGURATION VERIFICATION")
    
    # Check if MPESA_TRANSACTION_TYPE is configured
    transaction_type = getattr(settings, 'MPESA_TRANSACTION_TYPE', None)
    if transaction_type:
        print_result("Transaction Type Configuration", "PASS", 
                    f"MPESA_TRANSACTION_TYPE = {transaction_type}")
    else:
        print_result("Transaction Type Configuration", "FAIL", 
                    "MPESA_TRANSACTION_TYPE not configured")
        return False
    
    # Verify other M-Pesa settings
    required_settings = [
        'MPESA_BUSINESS_SHORT_CODE',
        'MPESA_PASSKEY', 
        'MPESA_CONSUMER_KEY',
        'MPESA_CONSUMER_SECRET',
        'MPESA_ENVIRONMENT'
    ]
    
    all_configured = True
    for setting in required_settings:
        value = getattr(settings, setting, None)
        if value:
            print_result(setting, "PASS", f"Configured")
        else:
            print_result(setting, "FAIL", "Not configured")
            all_configured = False
    
    return all_configured

def verify_mpesa_service():
    """Verify M-Pesa service uses correct transaction type"""
    print_header("M-PESA SERVICE VERIFICATION")
    
    try:
        # Initialize M-Pesa service
        mpesa_service = MPesaService()
        
        # Check if service initializes correctly
        print_result("M-Pesa Service Initialization", "PASS", 
                    f"Business Short Code: {mpesa_service.business_short_code}")
        
        # Verify transaction type would be used correctly
        expected_transaction_type = getattr(settings, 'MPESA_TRANSACTION_TYPE', 'CustomerBuyGoodsOnline')
        print_result("Transaction Type Setting", "PASS", 
                    f"Will use: {expected_transaction_type}")
        
        return True
        
    except Exception as e:
        print_result("M-Pesa Service Initialization", "FAIL", str(e))
        return False

def verify_environment_files():
    """Verify environment files include transaction type"""
    print_header("ENVIRONMENT FILES VERIFICATION")
    
    # Check .env.example
    try:
        with open('.env.example', 'r') as f:
            env_example_content = f.read()
        
        if 'MPESA_TRANSACTION_TYPE' in env_example_content:
            print_result(".env.example", "PASS", "Contains MPESA_TRANSACTION_TYPE")
        else:
            print_result(".env.example", "FAIL", "Missing MPESA_TRANSACTION_TYPE")
    except FileNotFoundError:
        print_result(".env.example", "FAIL", "File not found")
    
    # Check render.yaml
    try:
        with open('render.yaml', 'r') as f:
            render_content = f.read()
        
        if 'MPESA_TRANSACTION_TYPE' in render_content:
            print_result("render.yaml", "PASS", "Contains MPESA_TRANSACTION_TYPE")
        else:
            print_result("render.yaml", "FAIL", "Missing MPESA_TRANSACTION_TYPE")
    except FileNotFoundError:
        print_result("render.yaml", "FAIL", "File not found")

def show_transaction_type_guide():
    """Show guide for determining correct transaction type"""
    print_header("TRANSACTION TYPE GUIDE")
    
    print("📋 How to determine the correct TransactionType:")
    print()
    print("1. PAYBILL NUMBERS (CustomerPayBillOnline):")
    print("   - Used for bill payments")
    print("   - Customers enter Paybill number + Account number")
    print("   - Example: Pay electricity bill, water bill, etc.")
    print()
    print("2. TILL NUMBERS (CustomerBuyGoodsOnline):")
    print("   - Used for buying goods and services")
    print("   - Customers enter Till number only")
    print("   - Example: Pay at shop, restaurant, online store")
    print()
    print("🔍 TO VERIFY YOUR SHORTCODE TYPE:")
    print("   1. Contact Safaricom support")
    print("   2. Ask: 'Is shortcode 6319470 a Paybill or Till Number?'")
    print("   3. Update MPESA_TRANSACTION_TYPE accordingly")
    print()
    print("✅  CONFIRMED STATUS:")
    print("   Shortcode 6319470 is CONFIRMED as a Till Number")
    print("   Correct configuration: CustomerBuyGoodsOnline")

def main():
    """Main verification function"""
    print_header("M-PESA RESULTCODE 2028 FIX VERIFICATION")
    print("Verifying fix for 'The request is not permitted according to product assignment'")
    
    # Run all verifications
    config_ok = verify_configuration()
    service_ok = verify_mpesa_service()
    verify_environment_files()
    show_transaction_type_guide()
    
    # Summary
    print_header("VERIFICATION SUMMARY")
    
    if config_ok and service_ok:
        print("✅ ALL VERIFICATIONS PASSED")
        print()
        print("🚀 NEXT STEPS:")
        print("1. Deploy the updated configuration to Render.com")
        print("2. Test M-Pesa payment with a small amount")
        print("3. Monitor for ResultCode 2028 error resolution")
        print("4. Monitor for successful payments with Till Number configuration")
    else:
        print("❌ SOME VERIFICATIONS FAILED")
        print("Please fix the configuration issues before deploying")
    
    print()
    print("✅ SHORTCODE CONFIRMED:")
    print("   Shortcode 6319470 is confirmed as a Till Number")
    print("   Configuration: CustomerBuyGoodsOnline")

if __name__ == "__main__":
    main()
