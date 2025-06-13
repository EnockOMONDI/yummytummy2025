#!/usr/bin/env python3
"""
Test M-Pesa Callback Functionality
"""

import os
import sys
import django
import json

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'yummytummy_project.settings')
django.setup()

from django.test import Client
from yummytummy_store.models import Order, OrderTrackingStatus

def test_mpesa_callback():
    """Test M-Pesa callback processing"""
    print("📞 Testing M-Pesa Callback Processing")
    print("="*50)
    
    try:
        client = Client()
        
        # Get an M-Pesa order for testing
        mpesa_order = Order.objects.filter(payment_method='mpesa', payment_status='processing').first()
        if not mpesa_order:
            print("❌ No M-Pesa orders in processing status for testing")
            return
            
        print(f"✅ Testing with order: {mpesa_order.get_order_number()}")
        
        # Update order with M-Pesa checkout details for testing
        mpesa_order.mpesa_checkout_request_id = 'test_checkout_callback_123'
        mpesa_order.mpesa_merchant_request_id = 'test_merchant_callback_123'
        mpesa_order.save()
        
        # Test successful payment callback
        success_callback_data = {
            "Body": {
                "stkCallback": {
                    "MerchantRequestID": "test_merchant_callback_123",
                    "CheckoutRequestID": "test_checkout_callback_123",
                    "ResultCode": 0,
                    "ResultDesc": "The service request is processed successfully.",
                    "CallbackMetadata": {
                        "Item": [
                            {"Name": "Amount", "Value": int(mpesa_order.total_amount)},
                            {"Name": "MpesaReceiptNumber", "Value": "CALLBACK_TEST_456"},
                            {"Name": "TransactionDate", "Value": 20250613235000},
                            {"Name": "PhoneNumber", "Value": 254712345678}
                        ]
                    }
                }
            }
        }
        
        # Send successful callback
        response = client.post(
            '/mpesa-callback/',
            data=json.dumps(success_callback_data),
            content_type='application/json'
        )
        
        if response.status_code == 200:
            print("✅ M-Pesa callback processed successfully")
            
            # Check response
            response_data = response.json()
            if response_data.get('ResultCode') == 0:
                print("✅ Callback response format correct")
            else:
                print("❌ Callback response format incorrect")
                
            # Check if order was updated
            mpesa_order.refresh_from_db()
            if mpesa_order.payment_status == 'completed':
                print("✅ Order payment status updated to completed")
            else:
                print(f"❌ Order payment status not updated: {mpesa_order.payment_status}")
                
            if mpesa_order.mpesa_receipt_number == 'CALLBACK_TEST_456':
                print("✅ M-Pesa receipt number stored correctly")
            else:
                print(f"❌ M-Pesa receipt number not stored: {mpesa_order.mpesa_receipt_number}")
                
            # Check tracking status
            payment_status = mpesa_order.tracking_statuses.filter(status='payment_confirmed').last()
            if payment_status:
                print("✅ Payment confirmed tracking status created")
                print(f"   Message: {payment_status.message}")
            else:
                print("❌ Payment confirmed tracking status not created")
                
        else:
            print(f"❌ M-Pesa callback failed: {response.status_code}")
            
        # Test failed payment callback
        print("\n📞 Testing Failed Payment Callback")
        
        # Create another test order
        failed_order = Order.objects.filter(payment_method='mpesa', payment_status='processing').exclude(id=mpesa_order.id).first()
        if failed_order:
            failed_order.mpesa_checkout_request_id = 'test_failed_checkout_123'
            failed_order.mpesa_merchant_request_id = 'test_failed_merchant_123'
            failed_order.save()
            
            failed_callback_data = {
                "Body": {
                    "stkCallback": {
                        "MerchantRequestID": "test_failed_merchant_123",
                        "CheckoutRequestID": "test_failed_checkout_123",
                        "ResultCode": 1032,
                        "ResultDesc": "Request cancelled by user"
                    }
                }
            }
            
            response = client.post(
                '/mpesa-callback/',
                data=json.dumps(failed_callback_data),
                content_type='application/json'
            )
            
            if response.status_code == 200:
                print("✅ Failed payment callback processed")
                
                failed_order.refresh_from_db()
                if failed_order.payment_status == 'failed':
                    print("✅ Failed order status updated correctly")
                else:
                    print(f"❌ Failed order status not updated: {failed_order.payment_status}")
                    
                # Check cancelled tracking status
                cancelled_status = failed_order.tracking_statuses.filter(status='cancelled').last()
                if cancelled_status:
                    print("✅ Cancelled tracking status created")
                else:
                    print("❌ Cancelled tracking status not created")
            else:
                print(f"❌ Failed payment callback processing failed: {response.status_code}")
        
    except Exception as e:
        print(f"❌ M-Pesa Callback Test Error: {str(e)}")

if __name__ == "__main__":
    test_mpesa_callback()
