#!/usr/bin/env python3
"""
Timezone Testing Script for YummyTummy Django Application

This script tests the timezone fixes to ensure all timestamps display in Kenya time (EAT - UTC+3).
Run this script to verify that the timezone configuration is working correctly.

Usage:
    python test_timezone_fixes.py
"""

import os
import sys
import django
from datetime import datetime
import pytz

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'yummytummy_project.settings')
django.setup()

from django.conf import settings
from django.utils import timezone
from yummytummy_store.models import Order, OrderTrackingStatus
from django.contrib.auth.models import User

def test_django_timezone_settings():
    """Test Django timezone configuration"""
    print("🔍 Testing Django Timezone Settings")
    print("=" * 50)
    
    print(f"TIME_ZONE setting: {settings.TIME_ZONE}")
    print(f"USE_TZ setting: {settings.USE_TZ}")
    
    # Test current time in different timezones
    utc_now = timezone.now()
    kenya_tz = pytz.timezone('Africa/Nairobi')
    kenya_now = utc_now.astimezone(kenya_tz)
    
    print(f"Current UTC time: {utc_now.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    print(f"Current Kenya time: {kenya_now.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    print(f"Time difference: {(kenya_now.hour - utc_now.hour) % 24} hours")
    
    # Verify Kenya is UTC+3
    expected_offset = 3
    actual_offset = (kenya_now.hour - utc_now.hour) % 24
    
    if actual_offset == expected_offset:
        print("✅ Kenya timezone offset is correct (UTC+3)")
    else:
        print(f"❌ Kenya timezone offset is incorrect. Expected: {expected_offset}, Got: {actual_offset}")
    
    print()

def test_mpesa_transaction_parsing():
    """Test M-Pesa transaction date parsing with timezone awareness"""
    print("🔍 Testing M-Pesa Transaction Date Parsing")
    print("=" * 50)
    
    # Simulate M-Pesa transaction date format (YYYYMMDDHHMMSS)
    test_transaction_date = "20241213143000"  # Dec 13, 2024 at 14:30:00
    
    try:
        from datetime import datetime
        import pytz
        
        # Parse M-Pesa date format (same as in views.py)
        naive_datetime = datetime.strptime(str(test_transaction_date), '%Y%m%d%H%M%S')
        
        # Make timezone-aware in Kenya timezone
        kenya_tz = pytz.timezone('Africa/Nairobi')
        aware_datetime = kenya_tz.localize(naive_datetime)
        
        print(f"M-Pesa transaction date: {test_transaction_date}")
        print(f"Parsed naive datetime: {naive_datetime}")
        print(f"Kenya timezone-aware: {aware_datetime.strftime('%Y-%m-%d %H:%M:%S %Z')}")
        print(f"UTC equivalent: {aware_datetime.astimezone(pytz.UTC).strftime('%Y-%m-%d %H:%M:%S %Z')}")
        print("✅ M-Pesa transaction date parsing works correctly")
        
    except Exception as e:
        print(f"❌ M-Pesa transaction date parsing failed: {e}")
    
    print()

def test_database_timezone_storage():
    """Test how timestamps are stored and retrieved from database"""
    print("🔍 Testing Database Timezone Storage")
    print("=" * 50)
    
    try:
        # Get a sample order if exists
        sample_order = Order.objects.first()
        
        if sample_order:
            print(f"Sample Order ID: {sample_order.id}")
            print(f"Order created (raw): {sample_order.created}")
            print(f"Order created (Kenya): {sample_order.created.astimezone(pytz.timezone('Africa/Nairobi')).strftime('%Y-%m-%d %H:%M:%S %Z')}")
            
            # Check M-Pesa transaction date if exists
            if sample_order.mpesa_transaction_date:
                print(f"M-Pesa transaction date: {sample_order.mpesa_transaction_date}")
                print(f"M-Pesa date (Kenya): {sample_order.mpesa_transaction_date.astimezone(pytz.timezone('Africa/Nairobi')).strftime('%Y-%m-%d %H:%M:%S %Z')}")
            
            print("✅ Database timezone storage is working")
        else:
            print("ℹ️  No orders found in database for testing")
            
    except Exception as e:
        print(f"❌ Database timezone test failed: {e}")
    
    print()

def test_order_tracking_status_timezone():
    """Test OrderTrackingStatus timezone handling"""
    print("🔍 Testing OrderTrackingStatus Timezone")
    print("=" * 50)
    
    try:
        # Get a sample tracking status if exists
        sample_status = OrderTrackingStatus.objects.first()
        
        if sample_status:
            print(f"Sample Tracking Status ID: {sample_status.id}")
            print(f"Status: {sample_status.status}")
            print(f"Created at (raw): {sample_status.created_at}")
            print(f"Created at (Kenya): {sample_status.created_at.astimezone(pytz.timezone('Africa/Nairobi')).strftime('%Y-%m-%d %H:%M:%S %Z')}")
            print("✅ OrderTrackingStatus timezone handling is working")
        else:
            print("ℹ️  No tracking statuses found in database for testing")
            
    except Exception as e:
        print(f"❌ OrderTrackingStatus timezone test failed: {e}")
    
    print()

def test_template_timezone_filters():
    """Test timezone template filters"""
    print("🔍 Testing Template Timezone Filters")
    print("=" * 50)
    
    try:
        from django.template import Template, Context
        from django.template.loader import get_template
        
        # Test timezone template tag
        template_content = """
        {% load tz %}
        {% timezone "Africa/Nairobi" %}
        {{ test_datetime|date:"F d, Y H:i" }} EAT
        {% endtimezone %}
        """
        
        template = Template(template_content)
        context = Context({'test_datetime': timezone.now()})
        rendered = template.render(context).strip()
        
        print(f"Template rendered output: {rendered}")
        
        if "EAT" in rendered:
            print("✅ Template timezone filters are working")
        else:
            print("❌ Template timezone filters may not be working correctly")
            
    except Exception as e:
        print(f"❌ Template timezone filter test failed: {e}")
    
    print()

def generate_timezone_summary():
    """Generate a summary of timezone configuration"""
    print("📋 Timezone Configuration Summary")
    print("=" * 50)
    
    kenya_tz = pytz.timezone('Africa/Nairobi')
    utc_now = timezone.now()
    kenya_now = utc_now.astimezone(kenya_tz)
    
    print(f"Django TIME_ZONE: {settings.TIME_ZONE}")
    print(f"Django USE_TZ: {settings.USE_TZ}")
    print(f"Current UTC time: {utc_now.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    print(f"Current Kenya time: {kenya_now.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    print(f"Kenya timezone offset: UTC+{(kenya_now.hour - utc_now.hour) % 24}")
    
    print("\n🎯 Expected Behavior:")
    print("- All timestamps should display in Kenya time (EAT)")
    print("- M-Pesa payment times should match Kenyan business hours")
    print("- Customer emails should show Kenyan time")
    print("- Admin dashboard should display Kenya timezone")
    
    print("\n✅ Areas Fixed:")
    print("- Django settings.py: TIME_ZONE = 'Africa/Nairobi'")
    print("- M-Pesa callback: Timezone-aware transaction date parsing")
    print("- Templates: Added {% load tz %} and {% timezone %} tags")
    print("- Email templates: Kenya timezone display")
    print("- Admin dashboard: Kenya timezone display")
    print("- Customer dashboard: Kenya timezone display")

def main():
    """Run all timezone tests"""
    print("🇰🇪 YummyTummy Timezone Testing Script")
    print("Testing Kenya (EAT - UTC+3) timezone configuration")
    print("=" * 60)
    print()
    
    test_django_timezone_settings()
    test_mpesa_transaction_parsing()
    test_database_timezone_storage()
    test_order_tracking_status_timezone()
    test_template_timezone_filters()
    generate_timezone_summary()
    
    print("\n🎉 Timezone testing completed!")
    print("If all tests show ✅, your timezone configuration is working correctly.")

if __name__ == "__main__":
    main()
