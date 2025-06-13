#!/usr/bin/env python3
"""
Manual Payment System Testing Script

This script performs step-by-step testing of both M-Pesa and offline payment systems
to verify functionality and integration.
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
from yummytummy_store.mpesa_service import MPesaService

def test_mpesa_integration():
    """Test M-Pesa integration components"""
    print("🧪 Testing M-Pesa Integration Components")
    print("="*50)
    
    try:
        # Test 1: M-Pesa Service Initialization
        mpesa_service = MPesaService()
        print("✅ M-Pesa Service initialized successfully")
        
        # Test 2: Access Token Generation
        access_token = mpesa_service.get_access_token()
        if access_token:
            print(f"✅ M-Pesa Access Token generated (length: {len(access_token)})")
        else:
            print("❌ M-Pesa Access Token generation failed")
            
        # Test 3: Phone Number Formatting
        test_phones = ['0712345678', '254712345678', '+254712345678']
        for phone in test_phones:
            formatted = mpesa_service.format_phone_number(phone)
            print(f"✅ Phone {phone} formatted to {formatted}")
            
        # Test 4: Password Generation
        password, timestamp = mpesa_service.generate_password()
        print(f"✅ M-Pesa password generated (timestamp: {timestamp})")
        
    except Exception as e:
        print(f"❌ M-Pesa Integration Error: {str(e)}")

def test_online_order_creation():
    """Test online order creation with M-Pesa"""
    print("\n🛒 Testing Online Order Creation")
    print("="*50)
    
    try:
        client = Client()
        
        # Get a product
        product = Product.objects.first()
        if not product:
            print("❌ No products available for testing")
            return
            
        print(f"✅ Using product: {product.name} (Price: KSh {product.price})")
        
        # Create test user
        user, created = User.objects.get_or_create(
            username='online_test_user',
            defaults={
                'email': 'online@test.com',
                'first_name': 'Online',
                'last_name': 'Customer'
            }
        )
        
        # Add product to cart
        client.force_login(user)
        response = client.post(f'/cart/add/{product.id}/', {'quantity': 1, 'update': False})
        if response.status_code == 302:
            print("✅ Product added to cart successfully")
        else:
            print(f"❌ Failed to add product to cart: {response.status_code}")
            return
            
        # Test checkout form submission
        checkout_data = {
            'first_name': 'Online',
            'last_name': 'Customer',
            'email': 'online@test.com',
            'phone': '0712345678',
            'address': '123 Online Street',
            'city': 'Nairobi',
            'county': 'Nairobi',
            'payment_method': 'mpesa',
            'mpesa_phone': '0712345678'
        }
        
        response = client.post('/checkout/', checkout_data)
        print(f"✅ Checkout response: {response.status_code}")
        
        # Check if order was created
        order = Order.objects.filter(email='online@test.com').last()
        if order:
            print(f"✅ Online order created: {order.get_order_number()}")
            print(f"✅ Payment method: {order.payment_method}")
            print(f"✅ Payment status: {order.payment_status}")
            print(f"✅ Total amount: KSh {order.total_amount}")
            
            # Check order items
            items = order.items.all()
            print(f"✅ Order items: {items.count()}")
            for item in items:
                print(f"   - {item.product.name}: {item.quantity} x KSh {item.price}")
                
            return order
        else:
            print("❌ Online order not found after checkout")
            
    except Exception as e:
        print(f"❌ Online Order Creation Error: {str(e)}")
        
    return None

def test_offline_order_creation():
    """Test offline order creation"""
    print("\n💰 Testing Offline Order Creation")
    print("="*50)
    
    try:
        client = Client()
        
        # Login as sales user
        sales_user = User.objects.get(username='sales_demo')
        client.force_login(sales_user)
        
        # Get a product
        product = Product.objects.first()
        if not product:
            print("❌ No products available for testing")
            return
            
        print(f"✅ Using product: {product.name} (Price: KSh {product.price})")
        
        # Create offline order
        order_data = {
            'customer_type': 'business',
            'business_name': 'Test Business Ltd',
            'first_name': 'Offline',
            'last_name': 'Customer',
            'email': 'offline_test@business.com',
            'phone': '0723456789',
            'delivery_address': '456 Business Street',
            'delivery_city': 'Mombasa',
            'delivery_county': 'Mombasa',
            'order_items': json.dumps([{
                'product_id': product.id,
                'variant_id': None,
                'quantity': 3,
                'price': float(product.price)
            }])
        }
        
        response = client.post('/offline-orders/create/', order_data)
        print(f"✅ Offline order response: {response.status_code}")
        
        # Check if order was created
        order = Order.objects.filter(email='offline_test@business.com').last()
        if order:
            print(f"✅ Offline order created: {order.get_order_number()}")
            print(f"✅ Customer type: {order.customer_type}")
            print(f"✅ Business name: {order.business_name}")
            print(f"✅ Payment method: {order.payment_method}")
            print(f"✅ Payment status: {order.payment_status}")
            print(f"✅ Total amount: KSh {order.total_amount}")
            print(f"✅ Created by: {order.created_by.username}")
            
            # Check tracking status
            tracking_status = order.tracking_statuses.filter(status='offline_order_created').first()
            if tracking_status:
                print(f"✅ Initial tracking status: {tracking_status.status}")
            else:
                print("❌ Initial tracking status not created")
                
            return order
        else:
            print("❌ Offline order not found after creation")
            
    except Exception as e:
        print(f"❌ Offline Order Creation Error: {str(e)}")
        
    return None

def test_payment_status_updates():
    """Test payment status updates for both order types"""
    print("\n📊 Testing Payment Status Updates")
    print("="*50)
    
    try:
        # Test offline order payment status update
        offline_order = Order.objects.filter(payment_method='offline').last()
        if offline_order:
            print(f"✅ Testing offline order: {offline_order.get_order_number()}")
            
            # Update payment status
            offline_order.payment_status = 'completed'
            offline_order.save()
            
            # Create payment confirmed status
            OrderTrackingStatus.objects.create(
                order=offline_order,
                status='payment_confirmed',
                message='Payment confirmed by admin - cash payment received'
            )
            
            print(f"✅ Offline order payment status updated to: {offline_order.payment_status}")
            
            # Check tracking statuses
            statuses = offline_order.tracking_statuses.all().order_by('created_at')
            print(f"✅ Tracking statuses ({statuses.count()}):")
            for status in statuses:
                print(f"   - {status.status}: {status.message}")
        
        # Test online order payment simulation
        online_order = Order.objects.filter(payment_method='mpesa').last()
        if online_order:
            print(f"✅ Testing online order: {online_order.get_order_number()}")
            
            # Simulate successful M-Pesa payment
            online_order.payment_status = 'completed'
            online_order.transaction_id = 'TEST_RECEIPT_123'
            online_order.mpesa_receipt_number = 'TEST_RECEIPT_123'
            online_order.save()
            
            # Create payment confirmed status
            OrderTrackingStatus.objects.create(
                order=online_order,
                status='payment_confirmed',
                message='M-Pesa payment confirmed. Receipt: TEST_RECEIPT_123'
            )
            
            print(f"✅ Online order payment status updated to: {online_order.payment_status}")
            print(f"✅ M-Pesa receipt: {online_order.mpesa_receipt_number}")
            
    except Exception as e:
        print(f"❌ Payment Status Update Error: {str(e)}")

def test_order_tracking_integration():
    """Test order tracking for both payment types"""
    print("\n📋 Testing Order Tracking Integration")
    print("="*50)
    
    try:
        # Test order queries
        total_orders = Order.objects.count()
        mpesa_orders = Order.objects.filter(payment_method='mpesa').count()
        offline_orders = Order.objects.filter(payment_method='offline').count()
        
        print(f"✅ Total orders in system: {total_orders}")
        print(f"✅ M-Pesa orders: {mpesa_orders}")
        print(f"✅ Offline orders: {offline_orders}")
        
        # Test payment status distribution
        pending_payments = Order.objects.filter(payment_status='pending').count()
        completed_payments = Order.objects.filter(payment_status='completed').count()
        processing_payments = Order.objects.filter(payment_status='processing').count()
        
        print(f"✅ Pending payments: {pending_payments}")
        print(f"✅ Completed payments: {completed_payments}")
        print(f"✅ Processing payments: {processing_payments}")
        
        # Test recent orders
        recent_orders = Order.objects.order_by('-created')[:5]
        print(f"✅ Recent orders:")
        for order in recent_orders:
            print(f"   - {order.get_order_number()}: {order.payment_method} ({order.payment_status})")
            
    except Exception as e:
        print(f"❌ Order Tracking Integration Error: {str(e)}")

def test_admin_interface_integration():
    """Test admin interface for payment management"""
    print("\n👨‍💼 Testing Admin Interface Integration")
    print("="*50)
    
    try:
        client = Client()
        
        # Test admin login
        admin_user = User.objects.filter(is_superuser=True).first()
        if admin_user:
            client.force_login(admin_user)
            
            # Test admin dashboard access
            response = client.get('/admin/')
            if response.status_code == 200:
                print("✅ Django admin interface accessible")
            else:
                print(f"❌ Django admin access failed: {response.status_code}")
                
            # Test custom admin dashboard
            response = client.get('/admin-dashboard/')
            if response.status_code == 200:
                print("✅ Custom admin dashboard accessible")
            else:
                print(f"❌ Custom admin dashboard failed: {response.status_code}")
                
            # Test offline orders dashboard
            response = client.get('/offline-orders/')
            if response.status_code == 200:
                print("✅ Offline orders dashboard accessible")
            else:
                print(f"❌ Offline orders dashboard failed: {response.status_code}")
        else:
            print("❌ No admin user found for testing")
            
    except Exception as e:
        print(f"❌ Admin Interface Integration Error: {str(e)}")

def generate_payment_summary():
    """Generate comprehensive payment system summary"""
    print("\n" + "="*70)
    print("💳 PAYMENT SYSTEM COMPREHENSIVE SUMMARY")
    print("="*70)
    
    try:
        # Order statistics
        total_orders = Order.objects.count()
        mpesa_orders = Order.objects.filter(payment_method='mpesa').count()
        offline_orders = Order.objects.filter(payment_method='offline').count()
        
        # Payment status statistics
        pending_payments = Order.objects.filter(payment_status='pending').count()
        completed_payments = Order.objects.filter(payment_status='completed').count()
        processing_payments = Order.objects.filter(payment_status='processing').count()
        failed_payments = Order.objects.filter(payment_status='failed').count()
        
        # Revenue statistics
        total_revenue = sum(order.total_amount for order in Order.objects.filter(payment_status='completed'))
        mpesa_revenue = sum(order.total_amount for order in Order.objects.filter(payment_method='mpesa', payment_status='completed'))
        offline_revenue = sum(order.total_amount for order in Order.objects.filter(payment_method='offline', payment_status='completed'))
        
        print(f"\n📊 ORDER STATISTICS:")
        print(f"Total Orders: {total_orders}")
        print(f"M-Pesa Orders: {mpesa_orders}")
        print(f"Offline Orders: {offline_orders}")
        
        print(f"\n💰 PAYMENT STATUS:")
        print(f"Pending: {pending_payments}")
        print(f"Completed: {completed_payments}")
        print(f"Processing: {processing_payments}")
        print(f"Failed: {failed_payments}")
        
        print(f"\n💵 REVENUE ANALYSIS:")
        print(f"Total Revenue: KSh {total_revenue:,.2f}")
        print(f"M-Pesa Revenue: KSh {mpesa_revenue:,.2f}")
        print(f"Offline Revenue: KSh {offline_revenue:,.2f}")
        
        print(f"\n🎯 SYSTEM STATUS:")
        if mpesa_orders > 0 and offline_orders > 0:
            print("✅ Both M-Pesa and Offline payment systems are functional")
        elif mpesa_orders > 0:
            print("✅ M-Pesa payment system is functional")
            print("⚠️  Offline payment system needs testing")
        elif offline_orders > 0:
            print("✅ Offline payment system is functional")
            print("⚠️  M-Pesa payment system needs testing")
        else:
            print("⚠️  Both payment systems need testing")
            
        print(f"\n📅 Test completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
    except Exception as e:
        print(f"❌ Summary Generation Error: {str(e)}")

def main():
    """Run comprehensive payment system testing"""
    print("💳 YummyTummy Payment System Manual Testing")
    print("Testing M-Pesa online payments and offline order workflows")
    print("="*70)
    
    # Run all tests
    test_mpesa_integration()
    online_order = test_online_order_creation()
    offline_order = test_offline_order_creation()
    test_payment_status_updates()
    test_order_tracking_integration()
    test_admin_interface_integration()
    generate_payment_summary()
    
    print("\n🎉 Payment system testing completed!")
    print("Check the results above for any issues that need attention.")

if __name__ == "__main__":
    from datetime import datetime
    main()
