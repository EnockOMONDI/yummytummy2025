#!/usr/bin/env python
"""
Test script to verify Django security settings work correctly
in both development and production modes.
"""

import os
import sys
import django
from pathlib import Path

# Add the project directory to Python path
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

def test_development_mode():
    """Test security settings in development mode (DEBUG=True)"""
    print("🧪 TESTING DEVELOPMENT MODE (DEBUG=True)")
    print("=" * 50)
    
    # Set development environment
    os.environ['DEBUG'] = 'True'
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'yummytummy_project.settings')
    
    # Clear Django settings cache
    if hasattr(django.conf.settings, '_wrapped'):
        django.conf.settings._wrapped = None
    
    django.setup()
    from django.conf import settings
    
    print(f"✅ DEBUG: {settings.DEBUG}")
    print(f"✅ SECURE_SSL_REDIRECT: {getattr(settings, 'SECURE_SSL_REDIRECT', 'Not set (expected)')}")
    print(f"✅ SESSION_COOKIE_SECURE: {getattr(settings, 'SESSION_COOKIE_SECURE', 'Not set (expected)')}")
    print(f"✅ CSRF_COOKIE_SECURE: {getattr(settings, 'CSRF_COOKIE_SECURE', 'Not set (expected)')}")
    print(f"✅ SECURE_HSTS_SECONDS: {getattr(settings, 'SECURE_HSTS_SECONDS', 'Not set (expected)')}")
    
    # Verify security settings are NOT applied in development
    assert settings.DEBUG == True, "DEBUG should be True in development"
    assert not hasattr(settings, 'SECURE_SSL_REDIRECT') or settings.SECURE_SSL_REDIRECT == False, "SSL redirect should not be enabled in development"
    
    print("✅ Development mode test PASSED - Security settings correctly disabled")
    print()

def test_production_mode():
    """Test security settings in production mode (DEBUG=False)"""
    print("🚀 TESTING PRODUCTION MODE (DEBUG=False)")
    print("=" * 50)
    
    # Set production environment
    os.environ['DEBUG'] = 'False'
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'yummytummy_project.settings')
    
    # Clear Django settings cache
    if hasattr(django.conf.settings, '_wrapped'):
        django.conf.settings._wrapped = None
    
    django.setup()
    from django.conf import settings
    
    print(f"✅ DEBUG: {settings.DEBUG}")
    print(f"✅ SECURE_SSL_REDIRECT: {getattr(settings, 'SECURE_SSL_REDIRECT', 'Not set')}")
    print(f"✅ SESSION_COOKIE_SECURE: {getattr(settings, 'SESSION_COOKIE_SECURE', 'Not set')}")
    print(f"✅ CSRF_COOKIE_SECURE: {getattr(settings, 'CSRF_COOKIE_SECURE', 'Not set')}")
    print(f"✅ SECURE_HSTS_SECONDS: {getattr(settings, 'SECURE_HSTS_SECONDS', 'Not set')}")
    
    # Verify security settings ARE applied in production
    assert settings.DEBUG == False, "DEBUG should be False in production"
    assert hasattr(settings, 'SECURE_SSL_REDIRECT') and settings.SECURE_SSL_REDIRECT == True, "SSL redirect should be enabled in production"
    assert hasattr(settings, 'SESSION_COOKIE_SECURE') and settings.SESSION_COOKIE_SECURE == True, "Session cookies should be secure in production"
    assert hasattr(settings, 'CSRF_COOKIE_SECURE') and settings.CSRF_COOKIE_SECURE == True, "CSRF cookies should be secure in production"
    assert hasattr(settings, 'SECURE_HSTS_SECONDS') and settings.SECURE_HSTS_SECONDS == 31536000, "HSTS should be enabled with 1 year duration"
    
    print("✅ Production mode test PASSED - All security settings correctly enabled")
    print()

def main():
    """Run all security tests"""
    print("🔒 YUMMYTUMMY DJANGO SECURITY SETTINGS TEST")
    print("=" * 60)
    print()
    
    try:
        # Test development mode
        test_development_mode()
        
        # Test production mode  
        test_production_mode()
        
        print("🎉 ALL TESTS PASSED!")
        print("✅ Security settings are correctly configured for both development and production")
        print()
        print("📋 SUMMARY:")
        print("- Development (DEBUG=True): Security settings disabled for local development")
        print("- Production (DEBUG=False): All security settings enabled for deployment")
        print()
        print("🚀 Ready for production deployment on Render.com!")
        
    except Exception as e:
        print(f"❌ TEST FAILED: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
