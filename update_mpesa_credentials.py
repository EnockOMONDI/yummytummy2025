#!/usr/bin/env python3
"""
Script to safely update M-Pesa credentials in render.yaml
Helps you replace placeholder values with actual live credentials
"""

import re
import sys
from pathlib import Path


def update_render_yaml_credentials():
    """Interactive script to update M-Pesa credentials in render.yaml"""
    
    print("🔐 YummyTummy M-Pesa Credentials Update Tool")
    print("="*60)
    print("This script will help you update render.yaml with your live M-Pesa credentials.")
    print("⚠️  Make sure you have your live Safaricom credentials ready!")
    print()
    
    # Check if render.yaml exists
    render_yaml_path = Path("render.yaml")
    if not render_yaml_path.exists():
        print("❌ Error: render.yaml file not found!")
        print("Make sure you're running this script from the project root directory.")
        return False
    
    # Read current render.yaml
    with open(render_yaml_path, 'r') as f:
        content = f.read()
    
    print("📋 Current M-Pesa configuration in render.yaml:")
    print("-" * 50)
    
    # Extract current M-Pesa values
    mpesa_patterns = {
        'MPESA_BUSINESS_SHORT_CODE': r'MPESA_BUSINESS_SHORT_CODE.*?value:\s*["\']([^"\']*)["\']',
        'MPESA_PASSKEY': r'MPESA_PASSKEY.*?value:\s*["\']([^"\']*)["\']',
        'MPESA_CONSUMER_KEY': r'MPESA_CONSUMER_KEY.*?value:\s*["\']([^"\']*)["\']',
        'MPESA_CONSUMER_SECRET': r'MPESA_CONSUMER_SECRET.*?value:\s*["\']([^"\']*)["\']',
        'MPESA_ENVIRONMENT': r'MPESA_ENVIRONMENT.*?value:\s*["\']([^"\']*)["\']'
    }
    
    current_values = {}
    for key, pattern in mpesa_patterns.items():
        match = re.search(pattern, content, re.MULTILINE | re.DOTALL)
        if match:
            current_values[key] = match.group(1)
            # Mask sensitive values for display
            if key in ['MPESA_PASSKEY', 'MPESA_CONSUMER_SECRET']:
                display_value = f"{match.group(1)[:8]}...{match.group(1)[-4:]}" if len(match.group(1)) > 12 else "***MASKED***"
            else:
                display_value = match.group(1)
            print(f"   {key}: {display_value}")
        else:
            current_values[key] = None
            print(f"   {key}: NOT FOUND")
    
    print()
    
    # Check if credentials need updating
    needs_update = any(
        value in ['YOUR_LIVE_MPESA_PASSKEY_HERE', 'YOUR_LIVE_MPESA_CONSUMER_KEY_HERE', 'YOUR_LIVE_MPESA_CONSUMER_SECRET_HERE']
        for value in current_values.values()
    )
    
    if not needs_update:
        print("✅ M-Pesa credentials appear to be already set.")
        response = input("Do you want to update them anyway? (y/N): ").strip().lower()
        if response != 'y':
            print("No changes made.")
            return True
    
    print("🔧 Let's update your M-Pesa credentials:")
    print("(Press Enter to keep current value)")
    print()
    
    # Collect new credentials
    new_values = {}
    
    # Business Short Code
    current_short_code = current_values.get('MPESA_BUSINESS_SHORT_CODE', '6319470')
    new_short_code = input(f"Business Short Code [{current_short_code}]: ").strip()
    new_values['MPESA_BUSINESS_SHORT_CODE'] = new_short_code if new_short_code else current_short_code
    
    # Passkey
    current_passkey = current_values.get('MPESA_PASSKEY', '')
    if current_passkey and not current_passkey.startswith('YOUR_LIVE_'):
        passkey_prompt = f"M-Pesa Passkey [***CURRENT***]: "
    else:
        passkey_prompt = "M-Pesa Passkey: "
    
    new_passkey = input(passkey_prompt).strip()
    new_values['MPESA_PASSKEY'] = new_passkey if new_passkey else current_passkey
    
    # Consumer Key
    current_consumer_key = current_values.get('MPESA_CONSUMER_KEY', '')
    if current_consumer_key and not current_consumer_key.startswith('YOUR_LIVE_'):
        consumer_key_prompt = f"Consumer Key [***CURRENT***]: "
    else:
        consumer_key_prompt = "Consumer Key: "
    
    new_consumer_key = input(consumer_key_prompt).strip()
    new_values['MPESA_CONSUMER_KEY'] = new_consumer_key if new_consumer_key else current_consumer_key
    
    # Consumer Secret
    current_consumer_secret = current_values.get('MPESA_CONSUMER_SECRET', '')
    if current_consumer_secret and not current_consumer_secret.startswith('YOUR_LIVE_'):
        consumer_secret_prompt = f"Consumer Secret [***CURRENT***]: "
    else:
        consumer_secret_prompt = "Consumer Secret: "
    
    new_consumer_secret = input(consumer_secret_prompt).strip()
    new_values['MPESA_CONSUMER_SECRET'] = new_consumer_secret if new_consumer_secret else current_consumer_secret
    
    # Environment
    current_env = current_values.get('MPESA_ENVIRONMENT', 'production')
    print(f"\nEnvironment options: 'sandbox' (testing) or 'production' (live)")
    new_env = input(f"M-Pesa Environment [{current_env}]: ").strip()
    new_values['MPESA_ENVIRONMENT'] = new_env if new_env else current_env
    
    print()
    print("📋 Summary of changes:")
    print("-" * 30)
    for key, value in new_values.items():
        if key in ['MPESA_PASSKEY', 'MPESA_CONSUMER_SECRET']:
            display_value = f"{value[:8]}...{value[-4:]}" if value and len(value) > 12 else "***MASKED***"
        else:
            display_value = value
        print(f"   {key}: {display_value}")
    
    print()
    confirm = input("Apply these changes to render.yaml? (y/N): ").strip().lower()
    if confirm != 'y':
        print("No changes made.")
        return True
    
    # Apply changes to render.yaml
    updated_content = content
    
    for key, new_value in new_values.items():
        if new_value:  # Only update if value is provided
            pattern = f'(- key: {key}\\s+value:\\s*["\'])([^"\']*)(["\']\s*)'
            replacement = f'\\g<1>{new_value}\\g<3>'
            updated_content = re.sub(pattern, replacement, updated_content, flags=re.MULTILINE)
    
    # Write updated content
    try:
        with open(render_yaml_path, 'w') as f:
            f.write(updated_content)
        
        print("✅ render.yaml updated successfully!")
        print()
        print("🚀 Next steps:")
        print("1. Commit the changes: git add render.yaml")
        print("2. Push to yummy2 branch: git commit -m 'Update M-Pesa live credentials' && git push origin yummy2")
        print("3. Monitor deployment in Render dashboard")
        print("4. Run verification script: python verify_mpesa_deployment.py")
        
        return True
        
    except Exception as e:
        print(f"❌ Error updating render.yaml: {e}")
        return False


def main():
    """Main function"""
    try:
        success = update_render_yaml_credentials()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Operation cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
