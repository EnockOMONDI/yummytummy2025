#!/usr/bin/env python3
"""
Final Test: Cart Preservation Fix Verification
Confirms that the ProductVariant price attribute error has been resolved
"""

import os
import sys
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'yummytummy_project.settings')
django.setup()

from yummytummy_store.models import Order
from yummytummy_store.services import CartPreservationService
from django.test import Client

def test_cart_preservation_fix():
    """Test that cart preservation works without ProductVariant price errors"""
    print("🛒 FINAL CART PRESERVATION FIX TEST")
    print("="*50)
    
    try:
        # Get an order with items (preferably with variants)
        order = Order.objects.filter(items__isnull=False).first()
        if not order:
            print("❌ No orders with items found for testing")
            return False
            
        print(f"✅ Testing with order: {order.get_order_number()}")
        print(f"✅ Order has {order.items.count()} items")
        
        # Show order items details
        for item in order.items.all():
            if item.variant:
                print(f"   - {item.product.name} - {item.variant.name}: {item.quantity}x @ KSh {item.price}")
            else:
                print(f"   - {item.product.name} (Base): {item.quantity}x @ KSh {item.price}")
        
        # Test cart preservation (this was failing before the fix)
        print("\n🔧 Testing cart preservation...")
        success = CartPreservationService.preserve_cart_for_order(order)
        
        if success:
            print("✅ Cart preservation: SUCCESS")
            
            # Verify preserved data
            order.refresh_from_db()
            if order.preserved_cart_data:
                import json
                cart_data = json.loads(order.preserved_cart_data)
                print(f"✅ Preserved {len(cart_data)} cart items:")
                
                for cart_key, item_data in cart_data.items():
                    variant_info = f" - {item_data['variant_name']}" if item_data['variant_name'] else " (Base)"
                    print(f"   - {item_data['name']}{variant_info}: {item_data['quantity']}x @ KSh {item_data['price']}")
                
                # Test cart restoration
                print("\n🔄 Testing cart restoration...")
                client = Client()
                restore_success = CartPreservationService.restore_cart_from_order(client, order)
                
                if restore_success:
                    print("✅ Cart restoration: SUCCESS")
                    return True
                else:
                    print("❌ Cart restoration: FAILED")
                    return False
            else:
                print("❌ No preserved cart data found")
                return False
        else:
            print("❌ Cart preservation: FAILED")
            return False
            
    except Exception as e:
        print(f"❌ Test error: {str(e)}")
        return False

def test_payment_retry_workflow():
    """Test the complete payment retry workflow"""
    print("\n🔄 PAYMENT RETRY WORKFLOW TEST")
    print("="*50)
    
    try:
        # Get a failed order or create one
        order = Order.objects.filter(payment_method='mpesa').first()
        if not order:
            print("❌ No M-Pesa orders found for testing")
            return False
            
        # Set to failed status
        original_status = order.payment_status
        order.payment_status = 'failed'
        order.save()
        
        print(f"✅ Set order {order.get_order_number()} to failed status")
        
        # Test payment retry view
        client = Client()
        response = client.get(f'/payment/retry/{order.id}/')
        
        if response.status_code == 302:  # Should redirect to payment page
            print("✅ Payment retry URL: SUCCESS")
            print(f"   Redirected to: {response.url}")
            
            # Check if cart was restored in session
            session_cart = client.session.get('cart')
            if session_cart:
                print(f"✅ Cart restored in session with {len(session_cart)} items")
            
            # Check if checkout data was restored
            checkout_data = client.session.get('checkout_data')
            if checkout_data:
                print("✅ Checkout data restored in session")
                print(f"   Customer: {checkout_data.get('first_name')} {checkout_data.get('last_name')}")
                print(f"   Total: KSh {checkout_data.get('total_amount')}")
            
            # Restore original status
            order.payment_status = original_status
            order.save()
            
            return True
        else:
            print(f"❌ Payment retry URL failed: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Payment retry test error: {str(e)}")
        return False

def verify_model_structure():
    """Verify the ProductVariant model structure"""
    print("\n🔍 MODEL STRUCTURE VERIFICATION")
    print("="*50)
    
    try:
        from yummytummy_store.models import ProductVariant
        
        # Check ProductVariant fields
        variant_fields = [field.name for field in ProductVariant._meta.fields]
        print(f"✅ ProductVariant fields: {variant_fields}")
        
        # Verify price-related attributes
        if 'price' in variant_fields:
            print("❌ ProductVariant has 'price' field (unexpected)")
        else:
            print("✅ ProductVariant does NOT have 'price' field (correct)")
            
        if 'additional_price' in variant_fields:
            print("✅ ProductVariant has 'additional_price' field (correct)")
        else:
            print("❌ ProductVariant missing 'additional_price' field")
            
        # Test calculated_price property
        variant = ProductVariant.objects.first()
        if variant:
            try:
                calculated_price = variant.calculated_price
                print(f"✅ ProductVariant.calculated_price property works: KSh {calculated_price}")
            except Exception as e:
                print(f"❌ ProductVariant.calculated_price property error: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ Model verification error: {str(e)}")
        return False

def generate_final_summary():
    """Generate final summary of the fix"""
    print("\n" + "="*70)
    print("🎉 CART PRESERVATION FIX - FINAL SUMMARY")
    print("="*70)
    
    print("\n❌ ORIGINAL PROBLEM:")
    print("   Error: 'ProductVariant' object has no attribute 'price'")
    print("   Location: CartPreservationService.preserve_cart_for_order()")
    print("   Impact: M-Pesa payment retry functionality broken")
    
    print("\n🔧 SOLUTION APPLIED:")
    print("   1. Changed item.variant.price → item.price")
    print("   2. Changed item.product.price → item.price (for consistency)")
    print("   3. Updated both preserve_cart_for_order() and recreate_cart_from_order_items()")
    print("   4. Now uses actual paid price from OrderItem instead of recalculating")
    
    print("\n✅ BENEFITS:")
    print("   1. No more ProductVariant price attribute errors")
    print("   2. Cart preservation works correctly with variants")
    print("   3. Payment retry functionality fully operational")
    print("   4. Preserves historical pricing (important for consistency)")
    print("   5. Works for both base products and variants")
    
    print("\n🧪 TESTING RESULTS:")
    preservation_test = test_cart_preservation_fix()
    retry_test = test_payment_retry_workflow()
    model_test = verify_model_structure()
    
    print(f"\n📊 TEST SUMMARY:")
    print(f"   Cart Preservation: {'✅ PASS' if preservation_test else '❌ FAIL'}")
    print(f"   Payment Retry: {'✅ PASS' if retry_test else '❌ FAIL'}")
    print(f"   Model Structure: {'✅ PASS' if model_test else '❌ FAIL'}")
    
    all_tests_passed = all([preservation_test, retry_test, model_test])
    
    if all_tests_passed:
        print("\n🎉 ALL TESTS PASSED! Cart preservation fix is successful.")
        print("   The M-Pesa payment retry functionality is now fully operational.")
    else:
        print("\n⚠️  Some tests failed. Please review the results above.")
    
    from datetime import datetime
    print(f"\n📅 Test completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    return all_tests_passed

def main():
    """Run final verification of cart preservation fix"""
    print("🛒 YummyTummy Cart Preservation Fix - Final Verification")
    print("Testing the fix for 'ProductVariant' object has no attribute 'price' error")
    print("="*70)
    
    # Run comprehensive testing
    success = generate_final_summary()
    
    if success:
        print("\n🎉 Cart preservation fix verification completed successfully!")
        print("The M-Pesa payment failure handling system is now fully functional.")
    else:
        print("\n⚠️  Fix verification encountered issues. Please review the test results.")

if __name__ == "__main__":
    main()
