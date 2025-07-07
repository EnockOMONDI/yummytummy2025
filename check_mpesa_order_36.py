#!/usr/bin/env python3
"""
Check M-Pesa Order 36 Details and Transaction Status
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

from yummytummy_store.models import Order
from django.conf import settings

def check_order_36():
    """Check Order 36 details and M-Pesa transaction status"""
    print("🔍 M-PESA ORDER 36 INVESTIGATION")
    print("="*50)
    
    try:
        # Find order 36
        order = Order.objects.get(id=36)
        
        print("📋 ORDER DETAILS:")
        print(f"   ID: {order.id}")
        print(f"   Total Amount: KSH {order.total_amount}")
        print(f"   Payment Method: {order.payment_method}")
        print(f"   Payment Status: {order.payment_status}")
        print(f"   Customer Email: {order.email}")
        print(f"   Customer Phone: {order.phone}")
        print(f"   M-Pesa Phone: {order.mpesa_phone}")
        print(f"   Created: {order.created}")
        print(f"   Updated: {order.updated}")
        print()
        
        print("📱 M-PESA TRANSACTION DETAILS:")
        print(f"   Checkout Request ID: {order.mpesa_checkout_request_id}")
        print(f"   Merchant Request ID: {order.mpesa_merchant_request_id}")
        print(f"   Receipt Number: {order.mpesa_receipt_number}")
        print(f"   Transaction Date: {order.mpesa_transaction_date}")
        print(f"   Transaction ID: {order.transaction_id}")
        print()
        
        # Check if this matches the reported CheckoutRequestID
        expected_checkout_id = 'ws_CO_07072025221539652726436676'
        expected_merchant_id = '4544-49a4-a9e1-9a79c8cc90be3358831'
        
        print("🔍 TRANSACTION ID VERIFICATION:")
        if order.mpesa_checkout_request_id == expected_checkout_id:
            print("   ✅ CheckoutRequestID matches reported transaction")
        else:
            print("   ❌ CheckoutRequestID mismatch:")
            print(f"      Expected: {expected_checkout_id}")
            print(f"      Found: {order.mpesa_checkout_request_id}")
            
        if order.mpesa_merchant_request_id == expected_merchant_id:
            print("   ✅ MerchantRequestID matches reported transaction")
        else:
            print("   ❌ MerchantRequestID mismatch:")
            print(f"      Expected: {expected_merchant_id}")
            print(f"      Found: {order.mpesa_merchant_request_id}")
        print()
        
        # Check callback URL configuration
        print("🌐 CALLBACK URL CONFIGURATION:")
        site_url = getattr(settings, 'SITE_URL', 'Not configured')
        mpesa_callback_url = getattr(settings, 'MPESA_CALLBACK_URL', 'Not configured')
        
        print(f"   SITE_URL: {site_url}")
        print(f"   MPESA_CALLBACK_URL: {mpesa_callback_url}")
        
        # Expected callback URL after apex domain fix
        expected_callback = 'https://livegreat.co.ke/mpesa/callback/'
        if mpesa_callback_url == expected_callback:
            print("   ✅ Callback URL matches expected configuration")
        else:
            print("   ⚠️  Callback URL configuration:")
            print(f"      Expected: {expected_callback}")
            print(f"      Configured: {mpesa_callback_url}")
        print()
        
        # Analyze payment status
        print("💳 PAYMENT STATUS ANALYSIS:")
        if order.payment_status == 'failed':
            print("   ❌ Payment Status: FAILED")
            print("   📝 This confirms the payment failure reported")
        elif order.payment_status == 'processing':
            print("   ⏳ Payment Status: PROCESSING")
            print("   📝 Payment may still be pending callback")
        elif order.payment_status == 'completed':
            print("   ✅ Payment Status: COMPLETED")
            print("   📝 Payment was successful")
        else:
            print(f"   ❓ Payment Status: {order.payment_status}")
        
        # Check if callback was received
        if order.mpesa_receipt_number:
            print(f"   ✅ M-Pesa Receipt: {order.mpesa_receipt_number}")
            print("   📝 Callback was received and processed")
        else:
            print("   ❌ No M-Pesa Receipt Number")
            print("   📝 Callback may not have been received or processed")
            
        if order.transaction_id:
            print(f"   ✅ Transaction ID: {order.transaction_id}")
        else:
            print("   ❌ No Transaction ID")
            print("   📝 Transaction was not completed successfully")
        print()
        
        # Check order items
        print("🛒 ORDER ITEMS:")
        items = order.items.all()
        if items:
            for item in items:
                print(f"   - {item.product.name} (Qty: {item.quantity}) - KSH {item.price}")
        else:
            print("   No items found")
        print()
        
        return order
        
    except Order.DoesNotExist:
        print("❌ Order 36 not found in database")
        return None
    except Exception as e:
        print(f"❌ Error checking order: {e}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        return None

def check_recent_mpesa_orders():
    """Check recent M-Pesa orders for comparison"""
    print("📊 RECENT M-PESA ORDERS:")
    print("-" * 30)
    
    try:
        recent_orders = Order.objects.filter(
            payment_method='mpesa'
        ).order_by('-created')[:5]
        
        for order in recent_orders:
            status_icon = {
                'completed': '✅',
                'failed': '❌',
                'processing': '⏳',
                'pending': '⏸️'
            }.get(order.payment_status, '❓')
            
            print(f"   Order {order.id}: {status_icon} {order.payment_status} - KSH {order.total_amount} - {order.created.strftime('%Y-%m-%d %H:%M')}")
            if order.mpesa_checkout_request_id:
                print(f"      CheckoutRequestID: {order.mpesa_checkout_request_id}")
        print()
        
    except Exception as e:
        print(f"❌ Error checking recent orders: {e}")

if __name__ == "__main__":
    order = check_order_36()
    check_recent_mpesa_orders()
    
    if order:
        print("🎯 INVESTIGATION SUMMARY:")
        print("="*50)
        print("✅ Order 36 found in database")
        print("✅ Transaction details available for analysis")
        print("📝 Ready for callback log analysis")
    else:
        print("❌ Could not retrieve order details for investigation")
