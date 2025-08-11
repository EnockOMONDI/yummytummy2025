#!/usr/bin/env python3
"""
YummyTummy Django Project Setup Verification
Comprehensive test of the new Supabase database setup
"""

import os
import sys
import django
from django.core.management import execute_from_command_line

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'yummytummy_project.settings')
django.setup()

from django.db import connection
from django.contrib.auth.models import User
from yummytummy_store.models import Product, ProductVariant, Category

def test_database_connection():
    """Test basic database connectivity"""
    print("🔍 Testing Database Connection...")
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT version();")
            version = cursor.fetchone()
            print(f"✅ Database connected: {version[0]}")
            
            cursor.execute("SELECT current_database();")
            db_name = cursor.fetchone()
            print(f"📊 Database name: {db_name[0]}")
            
            cursor.execute("SELECT current_user;")
            user = cursor.fetchone()
            print(f"👤 Database user: {user[0]}")
            
        return True
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False

def test_django_models():
    """Test Django models and database tables"""
    print("\n🧪 Testing Django Models...")
    try:
        # Test User model
        user_count = User.objects.count()
        print(f"👥 Users in database: {user_count}")
        
        # Test YummyTummy models
        category_count = Category.objects.count()
        product_count = Product.objects.count()
        variant_count = ProductVariant.objects.count()
        
        print(f"📂 Categories: {category_count}")
        print(f"🛍️  Products: {product_count}")
        print(f"📦 Product Variants: {variant_count}")
        
        # Test if we can create a test category
        test_category, created = Category.objects.get_or_create(
            name="Test Category",
            defaults={'description': 'Test category for verification'}
        )
        
        if created:
            print("✅ Successfully created test category")
            test_category.delete()  # Clean up
            print("🧹 Test category cleaned up")
        else:
            print("ℹ️  Test category already exists")
            
        return True
    except Exception as e:
        print(f"❌ Django models test failed: {e}")
        return False

def test_admin_access():
    """Test admin interface accessibility"""
    print("\n🔐 Testing Admin Access...")
    try:
        superusers = User.objects.filter(is_superuser=True)
        if superusers.exists():
            print(f"✅ Found {superusers.count()} superuser(s)")
            for user in superusers:
                print(f"   - {user.username} ({user.email})")
        else:
            print("⚠️  No superusers found - you may need to create one")
            
        return True
    except Exception as e:
        print(f"❌ Admin access test failed: {e}")
        return False

def test_environment_variables():
    """Test critical environment variables"""
    print("\n🌍 Testing Environment Variables...")
    
    critical_vars = [
        'SECRET_KEY',
        'DATABASE_URL',
        'ALLOWED_HOSTS',
        'MPESA_BUSINESS_SHORT_CODE',
        'UPLOADCARE_PUBLIC_KEY'
    ]
    
    all_good = True
    for var in critical_vars:
        value = os.environ.get(var)
        if value:
            # Mask sensitive values
            if 'SECRET' in var or 'PASSWORD' in var:
                display_value = f"{value[:8]}..." if len(value) > 8 else "***"
            elif 'DATABASE_URL' in var:
                display_value = f"postgresql://...{value[-20:]}" if len(value) > 20 else value
            else:
                display_value = value
            print(f"✅ {var}: {display_value}")
        else:
            print(f"❌ {var}: Not set")
            all_good = False
    
    return all_good

def test_static_files():
    """Test static files configuration"""
    print("\n📁 Testing Static Files...")
    try:
        from django.conf import settings
        print(f"📂 STATIC_URL: {settings.STATIC_URL}")
        print(f"📁 STATIC_ROOT: {settings.STATIC_ROOT}")
        print(f"📋 STATICFILES_DIRS: {settings.STATICFILES_DIRS}")
        
        # Check if static directory exists
        if hasattr(settings, 'STATICFILES_DIRS') and settings.STATICFILES_DIRS:
            static_dir = settings.STATICFILES_DIRS[0]
            if os.path.exists(static_dir):
                print(f"✅ Static directory exists: {static_dir}")
            else:
                print(f"⚠️  Static directory not found: {static_dir}")
        
        return True
    except Exception as e:
        print(f"❌ Static files test failed: {e}")
        return False

def main():
    """Run all verification tests"""
    print("🧪 YUMMYTUMMY DJANGO PROJECT VERIFICATION")
    print("=" * 50)
    
    tests = [
        ("Database Connection", test_database_connection),
        ("Django Models", test_django_models),
        ("Admin Access", test_admin_access),
        ("Environment Variables", test_environment_variables),
        ("Static Files", test_static_files),
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n{'='*20} {test_name} {'='*20}")
        result = test_func()
        results.append((test_name, result))
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 VERIFICATION SUMMARY")
    print("=" * 50)
    
    passed = 0
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {test_name}")
        if result:
            passed += 1
    
    print(f"\n🎯 Results: {passed}/{len(tests)} tests passed")
    
    if passed == len(tests):
        print("\n🎉 ALL TESTS PASSED!")
        print("✅ Your YummyTummy Django project is ready!")
        print("💡 You can now run: python manage.py runserver")
    else:
        print(f"\n⚠️  {len(tests) - passed} test(s) failed")
        print("🔧 Please review the failed tests above")
    
    return passed == len(tests)

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
