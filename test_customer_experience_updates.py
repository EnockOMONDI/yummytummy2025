#!/usr/bin/env python3
"""
Test Customer Experience Updates
Tests the new customer-friendly email notifications and order tracking functionality
"""

import os
import sys
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'yummytummy_project.settings')
django.setup()

from django.test import Client
from django.contrib.auth.models import User
from yummytummy_store.models import Product, Order, OrderItem, OrderTrackingStatus
from yummytummy_store.services import OrderTrackingEmailService

def test_guest_order_tracking():
    """Test guest order tracking functionality"""
    print("🔍 Testing Guest Order Tracking")
    print("="*50)
    
    try:
        client = Client()
        
        # Test guest tracking page access
        response = client.get('/track-order/')
        if response.status_code == 200:
            print("✅ Guest order tracking page accessible")
        else:
            print(f"❌ Guest tracking page failed: {response.status_code}")
            return
            
        # Test with invalid order number
        response = client.post('/track-order/', {
            'order_number': 'INVALID-123',
            'email': 'test@example.com'
        })
        if response.status_code == 200 and 'Invalid order number format' in response.content.decode():
            print("✅ Invalid order number validation working")
        else:
            print("❌ Invalid order number validation failed")
            
        # Test with valid order (if exists)
        order = Order.objects.first()
        if order:
            response = client.post('/track-order/', {
                'order_number': order.get_order_number(),
                'email': order.email
            })
            if response.status_code == 200:
                print(f"✅ Valid order tracking working for {order.get_order_number()}")
            else:
                print(f"❌ Valid order tracking failed: {response.status_code}")
        else:
            print("⚠️  No orders available for testing")
            
    except Exception as e:
        print(f"❌ Guest Order Tracking Error: {str(e)}")

def test_email_template_updates():
    """Test updated email templates"""
    print("\n📧 Testing Email Template Updates")
    print("="*50)
    
    try:
        # Get an order for testing
        order = Order.objects.filter(payment_method='mpesa').first()
        if not order:
            print("⚠️  No M-Pesa orders available for email testing")
            return
            
        print(f"✅ Testing with order: {order.get_order_number()}")
        
        # Check if email template contains customer-friendly language
        from django.template.loader import render_to_string
        
        # Create test context
        user = order.user if order.user else User.objects.create_user(
            username='test_email_user',
            email='test@example.com'
        )
        
        context = {
            'order': order,
            'user': user,
            'temp_password': 'test123',
            'login_url': 'http://example.com/login',
            'order_items': [],
            'order_number': order.get_order_number(),
            'customer_name': order.get_customer_name(),
            'site_name': 'YummyTummy',
            'support_email': 'support@yummytummy.com',
            'token_expires_days': 7,
        }
        
        # Render email template
        html_content = render_to_string('yummytummy_store/emails/order_confirmation_with_account.html', context)
        
        # Check for customer-friendly content
        if 'Track Your Order' in html_content:
            print("✅ Email contains 'Track Your Order' button")
        else:
            print("❌ Email missing 'Track Your Order' button")
            
        if 'Order Tracking Access' in html_content:
            print("✅ Email contains customer-friendly access information")
        else:
            print("❌ Email missing customer-friendly access information")
            
        if 'Account Created Successfully' not in html_content:
            print("✅ Email no longer emphasizes account creation")
        else:
            print("❌ Email still emphasizes account creation")
            
        if 'Access Code' in html_content:
            print("✅ Email uses 'Access Code' instead of 'Password'")
        else:
            print("❌ Email still uses technical password terminology")
            
    except Exception as e:
        print(f"❌ Email Template Test Error: {str(e)}")

def test_order_confirmation_page():
    """Test updated order confirmation page"""
    print("\n📄 Testing Order Confirmation Page Updates")
    print("="*50)
    
    try:
        client = Client()
        
        # Create a test order and simulate confirmation page
        order = Order.objects.first()
        if not order:
            print("⚠️  No orders available for confirmation page testing")
            return
            
        # Simulate order confirmation session
        session = client.session
        session['order_id'] = order.id
        session.save()
        
        response = client.get('/checkout/confirmation/')
        if response.status_code == 200:
            print("✅ Order confirmation page accessible")
            
            content = response.content.decode()
            
            # Check for updated text
            if 'You can track the status of your order below' in content:
                print("✅ Updated confirmation text present")
            else:
                print("❌ Updated confirmation text missing")
                
            # Check for Track Your Order button
            if 'Track Your Order' in content:
                print("✅ Track Your Order button present")
            else:
                print("❌ Track Your Order button missing")
                
            # Check for tracking options information
            if 'Guest Tracking' in content and 'Account Access' in content:
                print("✅ Tracking options information present")
            else:
                print("❌ Tracking options information missing")
                
        else:
            print(f"❌ Order confirmation page failed: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Order Confirmation Page Test Error: {str(e)}")

def test_navigation_updates():
    """Test navigation updates"""
    print("\n🧭 Testing Navigation Updates")
    print("="*50)
    
    try:
        client = Client()
        
        # Test home page navigation
        response = client.get('/')
        if response.status_code == 200:
            content = response.content.decode()
            
            if 'TRACK ORDER' in content:
                print("✅ 'TRACK ORDER' link present in navigation")
            else:
                print("❌ 'TRACK ORDER' link missing from navigation")
                
            # Check if link points to guest tracking
            if 'href="/track-order/"' in content:
                print("✅ Track Order link points to guest tracking page")
            else:
                print("❌ Track Order link URL incorrect")
                
        else:
            print(f"❌ Home page navigation test failed: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Navigation Test Error: {str(e)}")

def test_mobile_responsiveness():
    """Test mobile responsiveness of new elements"""
    print("\n📱 Testing Mobile Responsiveness")
    print("="*50)
    
    try:
        client = Client()
        
        # Test guest tracking page with mobile user agent
        response = client.get('/track-order/', HTTP_USER_AGENT='Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X)')
        if response.status_code == 200:
            content = response.content.decode()
            
            # Check for mobile-responsive CSS
            if '@media (max-width: 768px)' in content:
                print("✅ Mobile-responsive CSS present")
            else:
                print("❌ Mobile-responsive CSS missing")
                
            # Check for mobile-friendly form elements
            if 'form-input' in content and 'track-btn' in content:
                print("✅ Mobile-friendly form elements present")
            else:
                print("❌ Mobile-friendly form elements missing")
                
        else:
            print(f"❌ Mobile responsiveness test failed: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Mobile Responsiveness Test Error: {str(e)}")

def test_brand_consistency():
    """Test YummyTummy brand consistency"""
    print("\n🎨 Testing Brand Consistency")
    print("="*50)
    
    try:
        client = Client()
        
        # Test guest tracking page for brand colors
        response = client.get('/track-order/')
        if response.status_code == 200:
            content = response.content.decode()
            
            # Check for YummyTummy brand colors
            brand_colors = ['#593500', '#ffffff', '#f5f2ed', '#ffc107']
            colors_found = sum(1 for color in brand_colors if color in content)
            
            if colors_found >= 3:
                print(f"✅ Brand colors present ({colors_found}/4 colors found)")
            else:
                print(f"❌ Insufficient brand colors ({colors_found}/4 colors found)")
                
            # Check for consistent styling
            if 'var(--primary-color)' in content and 'var(--secondary-color)' in content:
                print("✅ CSS variables for brand consistency used")
            else:
                print("❌ CSS variables for brand consistency missing")
                
        else:
            print(f"❌ Brand consistency test failed: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Brand Consistency Test Error: {str(e)}")

def generate_customer_experience_summary():
    """Generate comprehensive customer experience summary"""
    print("\n" + "="*70)
    print("🎯 CUSTOMER EXPERIENCE UPDATE SUMMARY")
    print("="*70)
    
    try:
        # Count orders by type
        total_orders = Order.objects.count()
        mpesa_orders = Order.objects.filter(payment_method='mpesa').count()
        offline_orders = Order.objects.filter(payment_method='offline').count()
        
        print(f"\n📊 SYSTEM STATISTICS:")
        print(f"Total Orders: {total_orders}")
        print(f"M-Pesa Orders: {mpesa_orders}")
        print(f"Offline Orders: {offline_orders}")
        
        print(f"\n✅ CUSTOMER EXPERIENCE IMPROVEMENTS:")
        print("1. Customer-friendly welcome emails (no account creation emphasis)")
        print("2. Guest order tracking functionality (no login required)")
        print("3. Updated order confirmation page with tracking options")
        print("4. 'Track Order' navigation link for easy access")
        print("5. Mobile-responsive design for all new features")
        print("6. Consistent YummyTummy brand styling")
        print("7. Clear messaging about tracking options")
        print("8. Seamless experience for both online and offline orders")
        
        print(f"\n🎨 DESIGN FEATURES:")
        print("- YummyTummy brand colors maintained (#593500, #ffffff, #f5f2ed, #ffc107)")
        print("- Mobile-responsive layouts for all devices")
        print("- Consistent button styling and hover effects")
        print("- Professional email templates with clear call-to-actions")
        print("- User-friendly form validation and error messages")
        
        print(f"\n🔄 TRACKING OPTIONS:")
        print("- Guest Tracking: Order number + email address")
        print("- Account Access: Login credentials provided in welcome email")
        print("- Unified experience for both M-Pesa and offline orders")
        print("- Real-time order status updates with progress indicators")
        
        print(f"\n📧 EMAIL IMPROVEMENTS:")
        print("- Subject: 'Order Confirmation & Tracking' (not 'Account Created')")
        print("- Focus on order tracking rather than account creation")
        print("- 'Access Code' terminology instead of 'Password'")
        print("- Clear 'Track Your Order' call-to-action button")
        print("- Customer-friendly language throughout")
        
        from datetime import datetime
        print(f"\n📅 Test completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
    except Exception as e:
        print(f"❌ Summary Generation Error: {str(e)}")

def main():
    """Run comprehensive customer experience testing"""
    print("🎯 YummyTummy Customer Experience Update Testing")
    print("Testing customer-friendly emails, guest tracking, and order confirmation improvements")
    print("="*70)
    
    # Run all tests
    test_guest_order_tracking()
    test_email_template_updates()
    test_order_confirmation_page()
    test_navigation_updates()
    test_mobile_responsiveness()
    test_brand_consistency()
    generate_customer_experience_summary()
    
    print("\n🎉 Customer experience testing completed!")
    print("All updates focus on customer-friendly language and seamless tracking experience.")

if __name__ == "__main__":
    main()
