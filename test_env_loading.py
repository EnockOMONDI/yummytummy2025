#!/usr/bin/env python3
"""
Test environment variable loading
"""

import os
from decouple import config

# Load environment variables
print("🔍 ENVIRONMENT VARIABLE LOADING TEST")
print("="*50)

# Test direct environment variable access
site_url_env = os.environ.get('SITE_URL', 'Not set in environment')
print(f"📋 Direct os.environ.get('SITE_URL'): {site_url_env}")

# Test decouple config access
site_url_config = config('SITE_URL', default='Not found by decouple')
print(f"📋 decouple config('SITE_URL'): {site_url_config}")

# Test with default fallback
site_url_with_default = config('SITE_URL', default='https://www.livegreat.co.ke')
print(f"📋 config with default fallback: {site_url_with_default}")

print()
print("🔍 EXPECTED vs ACTUAL:")
expected = 'https://livegreat.co.ke'
actual = site_url_config

if actual == expected:
    print(f"✅ Environment variable correctly set to: {actual}")
else:
    print(f"❌ Mismatch!")
    print(f"   Expected: {expected}")
    print(f"   Actual: {actual}")

print()
print("📁 .env FILE CONTENT:")
try:
    with open('.env', 'r') as f:
        for line_num, line in enumerate(f, 1):
            if 'SITE_URL' in line:
                print(f"   Line {line_num}: {line.strip()}")
except FileNotFoundError:
    print("   ❌ .env file not found")

print()
print("🔄 SOLUTION:")
print("   If the environment variable is not loading correctly,")
print("   restart the Django development server or application.")
