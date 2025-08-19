#!/usr/bin/env python3
"""
Test script to verify the opacity change in the About page hero section
"""

import requests
import re

def test_opacity_change():
    """Test that the opacity has been changed from 0.1 to 0.05"""
    
    print("🧪 TESTING ABOUT PAGE OPACITY CHANGE")
    print("=" * 50)
    
    # Test URL
    url = "http://127.0.0.1:8000/about/"
    
    try:
        # Make request to about page
        print("📡 Fetching about page content...")
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            print("✅ Page loads successfully (Status: 200)")
        else:
            print(f"❌ Page failed to load (Status: {response.status_code})")
            return False
            
        # Check for the opacity value in the CSS
        content = response.text
        
        # Look for the specific opacity setting in the about-hero::before rule
        opacity_pattern = r'\.about-hero::before[^}]*opacity:\s*([\d.]+);'
        opacity_match = re.search(opacity_pattern, content, re.DOTALL)
        
        if opacity_match:
            opacity_value = float(opacity_match.group(1))
            print(f"✅ Found opacity value: {opacity_value}")
            
            if opacity_value == 0.05:
                print("✅ Opacity correctly set to 0.05")
                return True
            elif opacity_value == 0.1:
                print("❌ Opacity still set to 0.1 (old value)")
                return False
            else:
                print(f"⚠️  Opacity set to unexpected value: {opacity_value}")
                return False
        else:
            # Alternative search for any opacity: 0.05 in the content
            if "opacity: 0.05;" in content:
                print("✅ Found opacity: 0.05; in page content")
                return True
            elif "opacity: 0.1;" in content:
                print("❌ Still found opacity: 0.1; in page content")
                return False
            else:
                print("❌ Could not find opacity setting in page content")
                return False
                
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to Django server")
        print("💡 Make sure Django development server is running:")
        print("   python manage.py runserver")
        return False
        
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

def test_background_image():
    """Test that the background image is still properly referenced"""
    
    print("\n🖼️  TESTING BACKGROUND IMAGE REFERENCE")
    print("=" * 50)
    
    url = "http://127.0.0.1:8000/about/"
    
    try:
        response = requests.get(url, timeout=10)
        content = response.text
        
        # Check for main.jpeg reference
        if "main.jpeg" in content:
            print("✅ Background image (main.jpeg) reference found")
            
            # Check for the complete background CSS rule
            bg_pattern = r'background:\s*url\([^)]*main\.jpeg[^)]*\)[^;]*center/cover'
            if re.search(bg_pattern, content):
                print("✅ Background image properly configured with center/cover")
                return True
            else:
                print("⚠️  Background image found but CSS might be incomplete")
                return True
        else:
            print("❌ Background image (main.jpeg) reference not found")
            return False
            
    except Exception as e:
        print(f"❌ Error testing background image: {e}")
        return False

if __name__ == "__main__":
    print("🔍 VERIFYING ABOUT PAGE HERO BACKGROUND OPACITY CHANGE")
    print("=" * 60)
    
    opacity_test = test_opacity_change()
    background_test = test_background_image()
    
    print("\n" + "=" * 60)
    print("📊 TEST RESULTS SUMMARY")
    print("=" * 60)
    
    if opacity_test and background_test:
        print("🎉 SUCCESS: Opacity change applied correctly!")
        print("✅ Background image opacity reduced from 0.1 to 0.05")
        print("✅ Background image reference maintained")
        print("💡 The main.jpeg background should now be more visible")
        exit(0)
    elif opacity_test:
        print("✅ Opacity change successful, but background image issue detected")
        exit(1)
    else:
        print("❌ Opacity change not detected or failed")
        exit(1)
