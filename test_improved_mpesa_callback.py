#!/usr/bin/env python3
"""
Comprehensive test script for the improved M-Pesa callback view.
Tests all the production-ready improvements implemented.
"""

import os
import sys
import django
import json
import time
from datetime import datetime

# Setup Django environment
sys.path.append('/Users/djsean/Desktop/APPS2024/MY APPS/yummytummy2025/maslove_project')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'yummytummy_project.settings')
django.setup()

from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from yummytummy_store.models import Order, OrderItem, Product, ProductVariant, OrderTrackingStatus
from decimal import Decimal

class ImprovedMPesaCallbackTest:
    """Test suite for improved M-Pesa callback functionality"""
    
    def __init__(self):
        self.client = Client()
        self.callback_url = reverse('yummytummy_store:mpesa_callback')
        self.test_results = []
        
    def log_test(self, test_name, passed, message=""):
        """Log test results"""
        status = "✅ PASS" if passed else "❌ FAIL"
        self.test_results.append({
            'test': test_name,
            'passed': passed,
            'message': message
        })
        print(f"{status}: {test_name}")
        if message:
            print(f"    {message}")
    
    def create_test_order(self):
        """Create a test order for callback testing"""
        # Create test user
        user = User.objects.create_user(
            username='testuser@example.com',
            email='testuser@example.com',
            first_name='Test',
            last_name='User'
        )
        
        # Create test order
        order = Order.objects.create(
            user=user,
            first_name='Test',
            last_name='User',
            email='testuser@example.com',
            phone='254712345678',
            address='Test Address',
            payment_method='mpesa',
            payment_status='pending',
            total_amount=Decimal('1000.00'),
            subtotal_amount=Decimal('1000.00'),
            mpesa_checkout_request_id='ws_CO_12345678901234567890'
        )
        
        return order
    
    def test_http_method_validation(self):
        """Test HTTP method validation"""
        # Test GET request (should fail)
        response = self.client.get(self.callback_url)
        passed = response.status_code == 405
        self.log_test("HTTP Method Validation (GET)", passed, 
                     f"Status: {response.status_code}, Expected: 405")
        
        # Test PUT request (should fail)
        response = self.client.put(self.callback_url)
        passed = response.status_code == 405
        self.log_test("HTTP Method Validation (PUT)", passed,
                     f"Status: {response.status_code}, Expected: 405")
    
    def test_json_parsing_errors(self):
        """Test JSON parsing error handling"""
        # Test empty body
        response = self.client.post(self.callback_url, data='', content_type='application/json')
        passed = response.status_code == 200 and response.json().get('ResultCode') == 1
        self.log_test("Empty JSON Body", passed,
                     f"ResultCode: {response.json().get('ResultCode')}, Expected: 1")
        
        # Test malformed JSON
        response = self.client.post(self.callback_url, data='{"invalid": json}', 
                                  content_type='application/json')
        passed = response.status_code == 200 and response.json().get('ResultCode') == 1
        self.log_test("Malformed JSON", passed,
                     f"ResultCode: {response.json().get('ResultCode')}, Expected: 1")
    
    def test_payload_validation(self):
        """Test callback payload validation"""
        # Test missing Body
        invalid_payload = {"InvalidStructure": "test"}
        response = self.client.post(self.callback_url, 
                                  data=json.dumps(invalid_payload),
                                  content_type='application/json')
        passed = response.status_code == 200 and response.json().get('ResultCode') == 1
        self.log_test("Missing Body Structure", passed,
                     f"ResultCode: {response.json().get('ResultCode')}, Expected: 1")
        
        # Test missing stkCallback
        invalid_payload = {"Body": {"InvalidCallback": "test"}}
        response = self.client.post(self.callback_url,
                                  data=json.dumps(invalid_payload),
                                  content_type='application/json')
        passed = response.status_code == 200 and response.json().get('ResultCode') == 1
        self.log_test("Missing stkCallback", passed,
                     f"ResultCode: {response.json().get('ResultCode')}, Expected: 1")
    
    def test_successful_payment_callback(self):
        """Test successful payment callback processing"""
        order = self.create_test_order()
        
        # Create successful payment callback payload
        successful_payload = {
            "Body": {
                "stkCallback": {
                    "MerchantRequestID": "29115-34620561-1",
                    "CheckoutRequestID": order.mpesa_checkout_request_id,
                    "ResultCode": 0,
                    "ResultDesc": "The service request is processed successfully.",
                    "AccountReference": str(order.id),
                    "CallbackMetadata": {
                        "Item": [
                            {"Name": "Amount", "Value": 1000.00},
                            {"Name": "MpesaReceiptNumber", "Value": "NLJ7RT61SV"},
                            {"Name": "TransactionDate", "Value": 20231201143022},
                            {"Name": "PhoneNumber", "Value": 254712345678}
                        ]
                    }
                }
            }
        }
        
        response = self.client.post(self.callback_url,
                                  data=json.dumps(successful_payload),
                                  content_type='application/json')
        
        # Verify response
        passed = response.status_code == 200 and response.json().get('ResultCode') == 0
        self.log_test("Successful Payment Response", passed,
                     f"Status: {response.status_code}, ResultCode: {response.json().get('ResultCode')}")
        
        # Verify order update
        order.refresh_from_db()
        passed = order.payment_status == 'completed' and order.mpesa_receipt_number == 'NLJ7RT61SV'
        self.log_test("Order Status Update", passed,
                     f"Status: {order.payment_status}, Receipt: {order.mpesa_receipt_number}")
        
        # Verify tracking status creation
        tracking_exists = OrderTrackingStatus.objects.filter(
            order=order, status='payment_confirmed'
        ).exists()
        self.log_test("Tracking Status Creation", tracking_exists,
                     f"Payment confirmed tracking status created: {tracking_exists}")
        
        # Cleanup
        order.delete()
    
    def test_failed_payment_callback(self):
        """Test failed payment callback processing"""
        order = self.create_test_order()
        
        # Create failed payment callback payload
        failed_payload = {
            "Body": {
                "stkCallback": {
                    "MerchantRequestID": "29115-34620561-1",
                    "CheckoutRequestID": order.mpesa_checkout_request_id,
                    "ResultCode": 1032,
                    "ResultDesc": "Request cancelled by user",
                    "AccountReference": str(order.id)
                }
            }
        }
        
        response = self.client.post(self.callback_url,
                                  data=json.dumps(failed_payload),
                                  content_type='application/json')
        
        # Verify response
        passed = response.status_code == 200 and response.json().get('ResultCode') == 0
        self.log_test("Failed Payment Response", passed,
                     f"Status: {response.status_code}, ResultCode: {response.json().get('ResultCode')}")
        
        # Verify order update
        order.refresh_from_db()
        passed = order.payment_status == 'failed'
        self.log_test("Failed Order Status Update", passed,
                     f"Status: {order.payment_status}, Expected: failed")
        
        # Verify tracking status creation
        tracking_exists = OrderTrackingStatus.objects.filter(
            order=order, status='cancelled'
        ).exists()
        self.log_test("Failed Tracking Status Creation", tracking_exists,
                     f"Cancelled tracking status created: {tracking_exists}")
        
        # Cleanup
        order.delete()
    
    def test_duplicate_callback_prevention(self):
        """Test duplicate callback prevention"""
        order = self.create_test_order()
        
        # First, process a successful payment
        order.payment_status = 'completed'
        order.transaction_id = 'NLJ7RT61SV'
        order.save()
        
        # Try to process the same callback again
        duplicate_payload = {
            "Body": {
                "stkCallback": {
                    "MerchantRequestID": "29115-34620561-1",
                    "CheckoutRequestID": order.mpesa_checkout_request_id,
                    "ResultCode": 0,
                    "ResultDesc": "The service request is processed successfully.",
                    "AccountReference": str(order.id),
                    "CallbackMetadata": {
                        "Item": [
                            {"Name": "Amount", "Value": 1000.00},
                            {"Name": "MpesaReceiptNumber", "Value": "DIFFERENT_RECEIPT"},
                            {"Name": "TransactionDate", "Value": 20231201143022}
                        ]
                    }
                }
            }
        }
        
        response = self.client.post(self.callback_url,
                                  data=json.dumps(duplicate_payload),
                                  content_type='application/json')
        
        # Verify duplicate is detected and handled
        passed = (response.status_code == 200 and 
                 response.json().get('ResultDesc') == 'Callback already processed')
        self.log_test("Duplicate Callback Prevention", passed,
                     f"ResultDesc: {response.json().get('ResultDesc')}")
        
        # Verify order wasn't changed
        order.refresh_from_db()
        passed = order.transaction_id == 'NLJ7RT61SV'  # Original receipt number
        self.log_test("Order Integrity After Duplicate", passed,
                     f"Receipt unchanged: {order.transaction_id}")
        
        # Cleanup
        order.delete()
    
    def test_order_not_found_handling(self):
        """Test handling when order is not found"""
        nonexistent_payload = {
            "Body": {
                "stkCallback": {
                    "MerchantRequestID": "29115-34620561-1",
                    "CheckoutRequestID": "ws_CO_NONEXISTENT123456",
                    "ResultCode": 0,
                    "ResultDesc": "The service request is processed successfully.",
                    "AccountReference": "999999"
                }
            }
        }
        
        response = self.client.post(self.callback_url,
                                  data=json.dumps(nonexistent_payload),
                                  content_type='application/json')
        
        # Should acknowledge callback even if order not found
        passed = (response.status_code == 200 and 
                 response.json().get('ResultDesc') == 'Order not found but callback acknowledged')
        self.log_test("Order Not Found Handling", passed,
                     f"ResultDesc: {response.json().get('ResultDesc')}")
    
    def run_all_tests(self):
        """Run all test cases"""
        print("🧪 Testing Improved M-Pesa Callback Implementation")
        print("=" * 60)
        
        start_time = time.time()
        
        # Run all tests
        self.test_http_method_validation()
        self.test_json_parsing_errors()
        self.test_payload_validation()
        self.test_successful_payment_callback()
        self.test_failed_payment_callback()
        self.test_duplicate_callback_prevention()
        self.test_order_not_found_handling()
        
        # Summary
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results if result['passed'])
        failed_tests = total_tests - passed_tests
        
        print("\n" + "=" * 60)
        print("📊 TEST SUMMARY")
        print("=" * 60)
        print(f"Total Tests: {total_tests}")
        print(f"✅ Passed: {passed_tests}")
        print(f"❌ Failed: {failed_tests}")
        print(f"⏱️  Duration: {time.time() - start_time:.2f} seconds")
        
        if failed_tests > 0:
            print("\n❌ FAILED TESTS:")
            for result in self.test_results:
                if not result['passed']:
                    print(f"  - {result['test']}: {result['message']}")
        
        success_rate = (passed_tests / total_tests) * 100
        print(f"\n🎯 Success Rate: {success_rate:.1f}%")
        
        return failed_tests == 0

if __name__ == '__main__':
    tester = ImprovedMPesaCallbackTest()
    success = tester.run_all_tests()
    
    if success:
        print("\n🎉 All tests passed! M-Pesa callback implementation is production-ready.")
    else:
        print("\n⚠️  Some tests failed. Please review the implementation.")
        sys.exit(1)
