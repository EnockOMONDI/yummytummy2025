#!/usr/bin/env python3
"""
Test script for the redesigned YummyTummy About page
"""

import requests
from bs4 import BeautifulSoup
import os

def test_about_page():
    """Test the about page functionality and content"""
    
    print("🧪 TESTING YUMMYTUMMY ABOUT PAGE")
    print("=" * 50)
    
    # Test URL
    url = "http://127.0.0.1:8000/about/"
    
    try:
        # Make request to about page
        print("📡 Testing page accessibility...")
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            print("✅ Page loads successfully (Status: 200)")
        else:
            print(f"❌ Page failed to load (Status: {response.status_code})")
            return False
            
        # Parse HTML content
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Test page title
        title = soup.find('title')
        if title and 'Live Great Limited' in title.text:
            print("✅ Page title updated correctly")
        else:
            print("❌ Page title not updated")
            
        # Test main heading
        main_heading = soup.find('h1')
        if main_heading and 'Live Great Limited' in main_heading.text:
            print("✅ Main heading found: Live Great Limited")
        else:
            print("❌ Main heading not found or incorrect")
            
        # Test mission section
        mission_found = False
        for h2 in soup.find_all('h2'):
            if 'Mission' in h2.text:
                mission_found = True
                break
        
        if mission_found:
            print("✅ Mission section found")
        else:
            print("❌ Mission section not found")
            
        # Test vision section
        vision_found = False
        for h2 in soup.find_all('h2'):
            if 'Vision' in h2.text:
                vision_found = True
                break
                
        if vision_found:
            print("✅ Vision section found")
        else:
            print("❌ Vision section not found")
            
        # Test core activities section
        activities_found = False
        for h2 in soup.find_all('h2'):
            if 'Core Activities' in h2.text:
                activities_found = True
                break
                
        if activities_found:
            print("✅ Core Activities section found")
        else:
            print("❌ Core Activities section not found")
            
        # Test specific content keywords
        content = response.text.lower()
        keywords = [
            'climate-smart',
            'peanut value addition',
            'sustainable sourcing',
            'community engagement',
            'nutrition gap',
            'unique value proposition'
        ]
        
        found_keywords = 0
        for keyword in keywords:
            if keyword in content:
                found_keywords += 1
                print(f"✅ Found keyword: {keyword}")
            else:
                print(f"❌ Missing keyword: {keyword}")
                
        # Test image references
        images = soup.find_all('img')
        expected_images = ['main.jpeg', 'IMG_7134.png', '1.jpeg']
        found_images = 0
        
        for img in images:
            src = img.get('src', '')
            for expected in expected_images:
                if expected in src:
                    found_images += 1
                    print(f"✅ Found image: {expected}")
                    break
                    
        # Test CSS styles
        style_blocks = soup.find_all('style')
        if style_blocks:
            print("✅ Custom CSS styles found")
            
            # Check for specific style classes
            style_content = ' '.join([block.text for block in style_blocks])
            style_classes = [
                'about-hero',
                'mission-vision',
                'core-activities',
                'solutions-section',
                'value-proposition'
            ]
            
            found_styles = 0
            for style_class in style_classes:
                if style_class in style_content:
                    found_styles += 1
                    print(f"✅ Found style class: {style_class}")
                else:
                    print(f"❌ Missing style class: {style_class}")
        else:
            print("❌ No custom CSS styles found")
            
        # Test responsive design
        if '@media' in response.text:
            print("✅ Responsive design styles found")
        else:
            print("❌ No responsive design styles found")
            
        # Summary
        print("\n" + "=" * 50)
        print("📊 TEST SUMMARY")
        print("=" * 50)
        
        total_tests = 8  # Adjust based on number of tests
        passed_tests = 0
        
        if response.status_code == 200:
            passed_tests += 1
        if title and 'Live Great Limited' in title.text:
            passed_tests += 1
        if main_heading and 'Live Great Limited' in main_heading.text:
            passed_tests += 1
        if mission_found:
            passed_tests += 1
        if vision_found:
            passed_tests += 1
        if activities_found:
            passed_tests += 1
        if found_keywords >= len(keywords) * 0.8:  # 80% of keywords found
            passed_tests += 1
        if found_images >= len(expected_images):
            passed_tests += 1
            
        print(f"🎯 Tests Passed: {passed_tests}/{total_tests}")
        
        if passed_tests == total_tests:
            print("🎉 ALL TESTS PASSED! About page redesign successful!")
        elif passed_tests >= total_tests * 0.8:
            print("✅ Most tests passed. About page is working well!")
        else:
            print("⚠️  Some tests failed. Please review the issues above.")
            
        return passed_tests >= total_tests * 0.8
        
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to Django server")
        print("💡 Make sure Django development server is running:")
        print("   python manage.py runserver")
        return False
        
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

if __name__ == "__main__":
    success = test_about_page()
    exit(0 if success else 1)
