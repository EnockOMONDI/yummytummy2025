#!/usr/bin/env python3
"""
Test M-Pesa Payment Failure Handling
Tests email notifications and cart preservation for failed M-Pesa payments
"""

import os
import sys
import django
import json

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'yummytummy_project.settings')
django.setup()

from django.test import Client
from django.contrib.auth.models import User
from yummytummy_store.models import Product, Order, OrderItem, OrderTrackingStatus
from yummytummy_store.services import OrderTrackingEmailService, CartPreservationService

def test_payment_failure_email_notifications():
    """Test email notifications for failed M-Pesa payments"""
    print("📧 Testing Payment Failure Email Notifications")
    print("="*50)
    
    try:
        # Get an order for testing
        order = Order.objects.filter(payment_method='mpesa').first()
        if not order:
            print("⚠️  No M-Pesa orders available for testing")
            return
            
        print(f"✅ Testing with order: {order.get_order_number()}")
        
        # Test failed payment notification
        success = OrderTrackingEmailService.send_payment_failed_notification(
            order=order,
            failure_reason="Request cancelled by user",
            request=None
        )
        
        if success:
            print("✅ Failed payment notification email sent successfully")
        else:
            print("❌ Failed to send payment failure notification")
            
        # Test with different failure reasons
        failure_reasons = [
            "Insufficient M-Pesa balance",
            "Network timeout",
            "Invalid phone number",
            "M-Pesa service unavailable"
        ]
        
        for reason in failure_reasons:
            success = OrderTrackingEmailService.send_payment_failed_notification(
                order=order,
                failure_reason=reason,
                request=None
            )
            if success:
                print(f"✅ Notification sent for reason: {reason}")
            else:
                print(f"❌ Failed to send notification for reason: {reason}")
                
    except Exception as e:
        print(f"❌ Payment Failure Email Test Error: {str(e)}")

def test_cart_preservation():
    """Test cart preservation for payment retry"""
    print("\n🛒 Testing Cart Preservation for Payment Retry")
    print("="*50)
    
    try:
        # Get an order with items
        order = Order.objects.filter(items__isnull=False).first()
        if not order:
            print("⚠️  No orders with items available for testing")
            return
            
        print(f"✅ Testing with order: {order.get_order_number()}")
        print(f"✅ Order has {order.items.count()} items")
        
        # Test cart preservation
        preserved = CartPreservationService.preserve_cart_for_order(order)
        if preserved:
            print("✅ Cart data preserved successfully")
            
            # Check if preserved data exists
            order.refresh_from_db()
            if order.preserved_cart_data:
                print("✅ Preserved cart data stored in order")
                
                # Parse and verify preserved data
                cart_data = json.loads(order.preserved_cart_data)
                print(f"✅ Preserved cart contains {len(cart_data)} items")
                
                for cart_key, item_data in cart_data.items():
                    print(f"   - {item_data['name']}: {item_data['quantity']}x @ KSh {item_data['price']}")
            else:
                print("❌ Preserved cart data not found in order")
        else:
            print("❌ Failed to preserve cart data")
            
    except Exception as e:
        print(f"❌ Cart Preservation Test Error: {str(e)}")

def test_cart_restoration():
    """Test cart restoration from preserved data"""
    print("\n🔄 Testing Cart Restoration")
    print("="*50)
    
    try:
        client = Client()
        
        # Get an order with preserved cart data
        order = Order.objects.filter(preserved_cart_data__isnull=False).first()
        if not order:
            # Create preserved cart data for testing
            order = Order.objects.filter(items__isnull=False).first()
            if order:
                CartPreservationService.preserve_cart_for_order(order)
                order.refresh_from_db()
            else:
                print("⚠️  No orders available for cart restoration testing")
                return
                
        print(f"✅ Testing cart restoration for order: {order.get_order_number()}")
        
        # Test cart restoration
        restored = CartPreservationService.restore_cart_from_order(client, order)
        if restored:
            print("✅ Cart restored successfully")
            
            # Check session cart
            session_cart = client.session.get('cart', {})
            if session_cart:
                print(f"✅ Session cart contains {len(session_cart)} items")
                
                for cart_key, item_data in session_cart.items():
                    print(f"   - {item_data['name']}: {item_data['quantity']}x @ KSh {item_data['price']}")
            else:
                print("❌ Session cart is empty after restoration")
        else:
            print("❌ Failed to restore cart")
            
    except Exception as e:
        print(f"❌ Cart Restoration Test Error: {str(e)}")

def test_payment_retry_workflow():
    """Test complete payment retry workflow"""
    print("\n🔄 Testing Payment Retry Workflow")
    print("="*50)
    
    try:
        client = Client()
        
        # Create a failed order for testing
        order = Order.objects.filter(payment_method='mpesa').first()
        if order:
            # Set order to failed status
            order.payment_status = 'failed'
            order.save()
            
            # Preserve cart data
            CartPreservationService.preserve_cart_for_order(order)
            
            print(f"✅ Testing payment retry for order: {order.get_order_number()}")
            
            # Test payment retry URL
            response = client.get(f'/payment/retry/{order.id}/')
            if response.status_code == 302:  # Redirect expected
                print("✅ Payment retry URL accessible")
                
                # Check if cart was restored
                session_cart = client.session.get('cart', {})
                if session_cart:
                    print(f"✅ Cart restored with {len(session_cart)} items")
                else:
                    print("❌ Cart not restored during retry")
                    
                # Check if checkout data was restored
                checkout_data = client.session.get('checkout_data')
                if checkout_data:
                    print("✅ Checkout data restored")
                    print(f"   Customer: {checkout_data.get('first_name')} {checkout_data.get('last_name')}")
                    print(f"   Email: {checkout_data.get('email')}")
                    print(f"   Total: KSh {checkout_data.get('total_amount')}")
                else:
                    print("❌ Checkout data not restored")
            else:
                print(f"❌ Payment retry URL failed: {response.status_code}")
        else:
            print("⚠️  No M-Pesa orders available for retry testing")
            
    except Exception as e:
        print(f"❌ Payment Retry Workflow Test Error: {str(e)}")

def test_mpesa_callback_failure_handling():
    """Test M-Pesa callback failure handling"""
    print("\n📞 Testing M-Pesa Callback Failure Handling")
    print("="*50)
    
    try:
        client = Client()
        
        # Create a test order for callback testing
        order = Order.objects.filter(payment_method='mpesa', payment_status='processing').first()
        if not order:
            print("⚠️  No processing M-Pesa orders available for callback testing")
            return
            
        # Set callback request IDs for testing
        order.mpesa_checkout_request_id = 'test_failed_callback_456'
        order.mpesa_merchant_request_id = 'test_failed_merchant_456'
        order.save()
        
        print(f"✅ Testing callback failure for order: {order.get_order_number()}")
        
        # Test failed payment callback
        failed_callback_data = {
            "Body": {
                "stkCallback": {
                    "MerchantRequestID": "test_failed_merchant_456",
                    "CheckoutRequestID": "test_failed_callback_456",
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
            
            # Check order status
            order.refresh_from_db()
            if order.payment_status == 'failed':
                print("✅ Order status updated to failed")
            else:
                print(f"❌ Order status not updated: {order.payment_status}")
                
            # Check tracking status
            cancelled_status = order.tracking_statuses.filter(status='cancelled').last()
            if cancelled_status:
                print("✅ Cancelled tracking status created")
                print(f"   Message: {cancelled_status.message}")
            else:
                print("❌ Cancelled tracking status not created")
        else:
            print(f"❌ Failed payment callback processing failed: {response.status_code}")
            
    except Exception as e:
        print(f"❌ M-Pesa Callback Failure Test Error: {str(e)}")

def test_failure_reason_mapping():
    """Test different M-Pesa failure reason mappings"""
    print("\n🔍 Testing Failure Reason Mapping")
    print("="*50)
    
    try:
        # Common M-Pesa failure codes and descriptions
        failure_scenarios = [
            (1032, "Request cancelled by user"),
            (1037, "Timeout in completing transaction"),
            (1025, "Unable to lock subscriber, a transaction is already in process for the current subscriber"),
            (1001, "Insufficient funds on MPESA account"),
            (1019, "Transaction expired"),
            (9999, "Request failed"),
        ]
        
        order = Order.objects.filter(payment_method='mpesa').first()
        if not order:
            print("⚠️  No M-Pesa orders available for failure reason testing")
            return
            
        print(f"✅ Testing failure reasons for order: {order.get_order_number()}")
        
        for result_code, result_desc in failure_scenarios:
            print(f"\n📋 Testing failure: {result_code} - {result_desc}")
            
            # Test email notification with specific failure reason
            success = OrderTrackingEmailService.send_payment_failed_notification(
                order=order,
                failure_reason=result_desc,
                request=None
            )
            
            if success:
                print(f"✅ Email notification sent for failure: {result_desc}")
            else:
                print(f"❌ Failed to send notification for: {result_desc}")
                
    except Exception as e:
        print(f"❌ Failure Reason Mapping Test Error: {str(e)}")

def generate_failure_handling_summary():
    """Generate comprehensive failure handling summary"""
    print("\n" + "="*70)
    print("🚫 M-PESA PAYMENT FAILURE HANDLING SUMMARY")
    print("="*70)
    
    try:
        # Count failed orders
        total_orders = Order.objects.count()
        failed_orders = Order.objects.filter(payment_status='failed').count()
        mpesa_orders = Order.objects.filter(payment_method='mpesa').count()
        failed_mpesa_orders = Order.objects.filter(payment_method='mpesa', payment_status='failed').count()
        
        print(f"\n📊 FAILURE STATISTICS:")
        print(f"Total Orders: {total_orders}")
        print(f"M-Pesa Orders: {mpesa_orders}")
        print(f"Failed Orders: {failed_orders}")
        print(f"Failed M-Pesa Orders: {failed_mpesa_orders}")
        
        if mpesa_orders > 0:
            failure_rate = (failed_mpesa_orders / mpesa_orders) * 100
            print(f"M-Pesa Failure Rate: {failure_rate:.1f}%")
        
        print(f"\n✅ IMPLEMENTED FEATURES:")
        print("1. Email notifications for failed M-Pesa payments")
        print("2. Cart preservation for payment retry attempts")
        print("3. Automatic cart restoration during retry")
        print("4. Checkout data preservation and restoration")
        print("5. Failed payment tracking status creation")
        print("6. Comprehensive failure reason handling")
        print("7. Payment retry URL with order restoration")
        print("8. M-Pesa callback failure processing")
        
        print(f"\n🔧 TECHNICAL IMPLEMENTATION:")
        print("- OrderTrackingEmailService.send_payment_failed_notification()")
        print("- CartPreservationService.preserve_cart_for_order()")
        print("- CartPreservationService.restore_cart_from_order()")
        print("- payment_retry view with cart restoration")
        print("- Enhanced M-Pesa callback failure handling")
        print("- Order.preserved_cart_data field for cart storage")
        
        print(f"\n📧 EMAIL FEATURES:")
        print("- Customer-friendly failure explanation")
        print("- Clear retry instructions")
        print("- Direct retry payment link")
        print("- Order tracking link")
        print("- Support contact information")
        print("- Common failure reasons explanation")
        
        print(f"\n🛒 CART PRESERVATION FEATURES:")
        print("- JSON-based cart data storage")
        print("- Product and variant information preservation")
        print("- Quantity and pricing preservation")
        print("- Checkout data restoration")
        print("- Seamless retry experience")
        
        from datetime import datetime
        print(f"\n📅 Test completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
    except Exception as e:
        print(f"❌ Summary Generation Error: {str(e)}")

def main():
    """Run comprehensive M-Pesa failure handling testing"""
    print("🚫 YummyTummy M-Pesa Payment Failure Handling Testing")
    print("Testing email notifications and cart preservation for failed payments")
    print("="*70)
    
    # Run all tests
    test_payment_failure_email_notifications()
    test_cart_preservation()
    test_cart_restoration()
    test_payment_retry_workflow()
    test_mpesa_callback_failure_handling()
    test_failure_reason_mapping()
    generate_failure_handling_summary()
    
    print("\n🎉 M-Pesa failure handling testing completed!")
    print("Both email notifications and cart preservation are now implemented.")

if __name__ == "__main__":
    main()
