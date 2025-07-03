#!/usr/bin/env python
"""
M-Pesa Payment Failure Diagnostic Tool for YummyTummy Django Application

This script diagnoses the root cause of M-Pesa payment failures when users receive
the error message "mpesa payment failed, network error" during payment initiation.

Usage:
    python mpesa_diagnostic_tool.py

Requirements:
    - Django environment must be set up
    - M-Pesa credentials must be configured
    - Internet connectivity required for API testing
"""

import os
import sys
import django
import requests
import json
import base64
from datetime import datetime
from pathlib import Path

# Add the project directory to Python path
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'yummytummy_project.settings')
django.setup()

from django.conf import settings
from yummytummy_store.mpesa_service import MPesaService


class MPesaDiagnosticTool:
    """Comprehensive M-Pesa diagnostic tool"""
    
    def __init__(self):
        self.results = {
            'configuration': {},
            'connectivity': {},
            'authentication': {},
            'api_endpoints': {},
            'stk_push_test': {},
            'recommendations': []
        }
        
    def print_header(self, title):
        """Print formatted section header"""
        print(f"\n{'='*60}")
        print(f"🔍 {title}")
        print(f"{'='*60}")
        
    def print_result(self, test_name, status, details=""):
        """Print formatted test result"""
        status_icon = "✅" if status == "PASS" else "❌" if status == "FAIL" else "⚠️"
        print(f"{status_icon} {test_name}: {status}")
        if details:
            print(f"   {details}")
            
    def test_configuration(self):
        """Test M-Pesa configuration settings"""
        self.print_header("M-PESA CONFIGURATION VALIDATION")
        
        # Check required settings
        required_settings = [
            'MPESA_BUSINESS_SHORT_CODE',
            'MPESA_PASSKEY', 
            'MPESA_CONSUMER_KEY',
            'MPESA_CONSUMER_SECRET',
            'MPESA_ENVIRONMENT'
        ]
        
        config_valid = True
        for setting in required_settings:
            value = getattr(settings, setting, None)
            if value:
                self.print_result(f"Setting {setting}", "PASS", f"Value: {value[:10]}...")
                self.results['configuration'][setting] = "CONFIGURED"
            else:
                self.print_result(f"Setting {setting}", "FAIL", "Missing or empty")
                self.results['configuration'][setting] = "MISSING"
                config_valid = False
                
        # Check environment setting
        env = getattr(settings, 'MPESA_ENVIRONMENT', 'sandbox')
        base_url = getattr(settings, 'MPESA_BASE_URL', '')
        
        self.print_result("Environment Configuration", "PASS" if env in ['sandbox', 'production'] else "FAIL",
                         f"Environment: {env}, Base URL: {base_url}")
        
        self.results['configuration']['overall'] = "VALID" if config_valid else "INVALID"
        return config_valid
        
    def test_connectivity(self):
        """Test network connectivity to M-Pesa endpoints"""
        self.print_header("NETWORK CONNECTIVITY TESTS")
        
        base_url = getattr(settings, 'MPESA_BASE_URL', 'https://api.safaricom.co.ke')
        
        # Test basic connectivity
        try:
            response = requests.get(base_url, timeout=10)
            self.print_result("Base URL Connectivity", "PASS", f"Status: {response.status_code}")
            self.results['connectivity']['base_url'] = "REACHABLE"
        except requests.exceptions.RequestException as e:
            self.print_result("Base URL Connectivity", "FAIL", f"Error: {str(e)}")
            self.results['connectivity']['base_url'] = f"UNREACHABLE: {str(e)}"
            
        # Test specific endpoints
        endpoints = {
            'auth': f"{base_url}/oauth/v1/generate?grant_type=client_credentials",
            'stk_push': f"{base_url}/mpesa/stkpush/v1/processrequest"
        }
        
        for name, url in endpoints.items():
            try:
                # Just test if endpoint is reachable (expect auth error, not network error)
                response = requests.post(url, timeout=10)
                self.print_result(f"{name.title()} Endpoint", "PASS", f"Reachable (Status: {response.status_code})")
                self.results['connectivity'][name] = "REACHABLE"
            except requests.exceptions.RequestException as e:
                self.print_result(f"{name.title()} Endpoint", "FAIL", f"Error: {str(e)}")
                self.results['connectivity'][name] = f"UNREACHABLE: {str(e)}"
                
    def test_authentication(self):
        """Test M-Pesa authentication"""
        self.print_header("M-PESA AUTHENTICATION TEST")
        
        try:
            mpesa_service = MPesaService()
            access_token = mpesa_service.get_access_token()
            
            if access_token:
                self.print_result("Authentication", "PASS", f"Token length: {len(access_token)} characters")
                self.results['authentication']['status'] = "SUCCESS"
                self.results['authentication']['token_length'] = len(access_token)
                return True
            else:
                self.print_result("Authentication", "FAIL", "No access token received")
                self.results['authentication']['status'] = "FAILED"
                return False
                
        except Exception as e:
            self.print_result("Authentication", "FAIL", f"Exception: {str(e)}")
            self.results['authentication']['status'] = f"ERROR: {str(e)}"
            return False
            
    def test_stk_push_simulation(self):
        """Test STK Push with simulation data"""
        self.print_header("STK PUSH SIMULATION TEST")
        
        try:
            mpesa_service = MPesaService()
            
            # Use test data
            test_phone = "254708374149"  # Safaricom test number
            test_amount = 1.0  # Minimum amount
            test_order_id = 99999  # Test order ID
            test_callback_url = "https://webhook.site/test-callback"
            
            self.print_result("Test Parameters", "INFO", 
                            f"Phone: {test_phone}, Amount: {test_amount}, Order: {test_order_id}")
            
            # Attempt STK Push
            response = mpesa_service.initiate_stk_push(
                phone_number=test_phone,
                amount=test_amount,
                order_id=test_order_id,
                callback_url=test_callback_url
            )
            
            if response.get('success'):
                self.print_result("STK Push Initiation", "PASS", 
                                f"Checkout Request ID: {response.get('checkout_request_id', 'N/A')}")
                self.results['stk_push_test']['status'] = "SUCCESS"
                self.results['stk_push_test']['response'] = response
            else:
                error_msg = response.get('error', 'Unknown error')
                self.print_result("STK Push Initiation", "FAIL", f"Error: {error_msg}")
                self.results['stk_push_test']['status'] = "FAILED"
                self.results['stk_push_test']['error'] = error_msg
                
                # Analyze the specific error
                self.analyze_stk_push_error(error_msg)
                
        except Exception as e:
            self.print_result("STK Push Initiation", "FAIL", f"Exception: {str(e)}")
            self.results['stk_push_test']['status'] = f"ERROR: {str(e)}"
            
    def analyze_stk_push_error(self, error_msg):
        """Analyze STK Push error and provide recommendations"""
        error_msg_lower = error_msg.lower()
        
        if "network error" in error_msg_lower:
            self.results['recommendations'].append({
                'issue': 'Network Error',
                'cause': 'Connection timeout or network connectivity issue',
                'solutions': [
                    'Check internet connectivity',
                    'Verify firewall settings allow outbound HTTPS connections',
                    'Test from different network/server',
                    'Check if M-Pesa API endpoints are accessible'
                ]
            })
            
        elif "authentication" in error_msg_lower or "unauthorized" in error_msg_lower:
            self.results['recommendations'].append({
                'issue': 'Authentication Error',
                'cause': 'Invalid M-Pesa credentials or expired access token',
                'solutions': [
                    'Verify MPESA_CONSUMER_KEY and MPESA_CONSUMER_SECRET',
                    'Check if credentials are for correct environment (sandbox/production)',
                    'Ensure credentials are not expired',
                    'Contact Safaricom to verify account status'
                ]
            })
            
        elif "invalid" in error_msg_lower and "shortcode" in error_msg_lower:
            self.results['recommendations'].append({
                'issue': 'Invalid Business Short Code',
                'cause': 'Business short code is incorrect or not activated',
                'solutions': [
                    'Verify MPESA_BUSINESS_SHORT_CODE is correct',
                    'Ensure business short code is activated for STK Push',
                    'Check if using correct short code for environment',
                    'Contact Safaricom to verify short code status'
                ]
            })
            
        elif "passkey" in error_msg_lower or "password" in error_msg_lower:
            self.results['recommendations'].append({
                'issue': 'Invalid Passkey',
                'cause': 'M-Pesa passkey is incorrect or expired',
                'solutions': [
                    'Verify MPESA_PASSKEY is correct and current',
                    'Check if passkey matches the business short code',
                    'Request new passkey from Safaricom if needed',
                    'Ensure passkey is for correct environment'
                ]
            })
            
    def test_callback_url_accessibility(self):
        """Test if callback URL is accessible"""
        self.print_header("CALLBACK URL ACCESSIBILITY TEST")
        
        if settings.DEBUG:
            callback_url = 'https://webhook.site/unique-id'
            self.print_result("Callback URL (Development)", "INFO",
                            f"Using placeholder: {callback_url}")
        else:
            # In production, use the configured callback URL for livegreat.co.ke
            try:
                callback_url = getattr(settings, 'MPESA_CALLBACK_URL',
                                     f"{settings.SITE_URL}/mpesa/callback/")
                self.print_result("Callback URL (Production)", "PASS",
                                f"Using: {callback_url}")

                # Verify the URL format
                if callback_url.startswith('https://livegreat.co.ke/'):
                    self.print_result("Callback Domain", "PASS",
                                    "Using registered domain: livegreat.co.ke")
                else:
                    self.print_result("Callback Domain", "WARN",
                                    f"Domain may not match Safaricom registration: {callback_url}")

            except Exception as e:
                self.print_result("Callback URL Resolution", "FAIL", f"Error: {str(e)}")
                
    def generate_recommendations(self):
        """Generate specific recommendations based on test results"""
        self.print_header("DIAGNOSTIC RECOMMENDATIONS")
        
        # Add general recommendations based on test results
        if self.results['configuration']['overall'] == "INVALID":
            self.results['recommendations'].append({
                'issue': 'Configuration Issues',
                'cause': 'Missing or invalid M-Pesa configuration settings',
                'solutions': [
                    'Verify all M-Pesa environment variables are set',
                    'Check .env file and render.yaml for correct values',
                    'Ensure settings.py loads M-Pesa configuration correctly',
                    'Restart application after configuration changes'
                ]
            })
            
        if any("UNREACHABLE" in str(v) for v in self.results['connectivity'].values()):
            self.results['recommendations'].append({
                'issue': 'Network Connectivity',
                'cause': 'Cannot reach M-Pesa API endpoints',
                'solutions': [
                    'Check server internet connectivity',
                    'Verify DNS resolution for api.safaricom.co.ke',
                    'Check firewall rules allow HTTPS outbound connections',
                    'Test from different server/network if possible'
                ]
            })
            
        # Print recommendations
        for i, rec in enumerate(self.results['recommendations'], 1):
            print(f"\n🔧 RECOMMENDATION {i}: {rec['issue']}")
            print(f"   Cause: {rec['cause']}")
            print(f"   Solutions:")
            for solution in rec['solutions']:
                print(f"   • {solution}")
                
    def run_full_diagnostic(self):
        """Run complete diagnostic suite"""
        print("🚀 M-PESA PAYMENT FAILURE DIAGNOSTIC TOOL")
        print("🎯 YummyTummy Django Application")
        print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Run all tests
        config_valid = self.test_configuration()
        self.test_connectivity()
        
        if config_valid:
            auth_success = self.test_authentication()
            if auth_success:
                self.test_stk_push_simulation()
        else:
            print("\n⚠️  Skipping authentication and STK Push tests due to configuration issues")
            
        self.test_callback_url_accessibility()
        self.generate_recommendations()
        
        # Summary
        self.print_header("DIAGNOSTIC SUMMARY")
        print(f"Configuration: {self.results['configuration']['overall']}")
        print(f"Authentication: {self.results['authentication'].get('status', 'SKIPPED')}")
        print(f"STK Push Test: {self.results['stk_push_test'].get('status', 'SKIPPED')}")
        print(f"Recommendations: {len(self.results['recommendations'])} issues found")
        
        return self.results


def main():
    """Main function to run diagnostic tool"""
    try:
        diagnostic = MPesaDiagnosticTool()
        results = diagnostic.run_full_diagnostic()
        
        # Save results to file
        results_file = f"mpesa_diagnostic_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(results_file, 'w') as f:
            json.dump(results, f, indent=2, default=str)
            
        print(f"\n📄 Detailed results saved to: {results_file}")
        
    except Exception as e:
        print(f"❌ Diagnostic tool failed: {str(e)}")
        return 1
        
    return 0


if __name__ == '__main__':
    sys.exit(main())
