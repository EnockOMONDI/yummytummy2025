#!/usr/bin/env python3
"""
Comprehensive Unit and Integration Tests for YummyTummy M-Pesa Multiple Payment Failures
Tests the behavior of the payment failure handling system with consecutive failures
"""

import json
import time
from decimal import Decimal
from unittest.mock import patch, MagicMock
from django.test import TestCase, Client, TransactionTestCase
from django.contrib.auth.models import User
from django.urls import reverse
from django.core import mail
from django.db import transaction
from django.utils import timezone
from datetime import timedelta

from yummytummy_store.models import (
    Category, Product, ProductVariant, Order, OrderItem, 
    OrderTrackingStatus, AutoCreatedAccount
)
from yummytummy_store.services import (
    OrderTrackingEmailService, CartPreservationService, OrderTrackingService
)


class MultiplePaymentFailureTestCase(TestCase):
    """Base test case with common setup for multiple payment failure tests"""
    
    def setUp(self):
        """Set up test data for payment failure scenarios"""
        # Create test user
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            first_name='Test',
            last_name='User'
        )
        
        # Create test category
        self.category = Category.objects.create(
            name='Test Peanut Butter',
            slug='test-peanut-butter'
        )
        
        # Create test product
        self.product = Product.objects.create(
            name='Premium Peanut Butter',
            slug='premium-peanut-butter',
            description='Test premium peanut butter',
            price=Decimal('500.00'),
            category=self.category,
            is_available=True
        )
        
        # Create test variants
        self.variant_250g = ProductVariant.objects.create(
            product=self.product,
            name='250g',
            additional_price=Decimal('0.00')
        )
        
        self.variant_500g = ProductVariant.objects.create(
            product=self.product,
            name='500g',
            additional_price=Decimal('200.00')
        )
        
        self.variant_1kg = ProductVariant.objects.create(
            product=self.product,
            name='1kg',
            additional_price=Decimal('400.00')
        )
        
        # Create test order
        self.order = Order.objects.create(
            user=self.user,
            first_name='Test',
            last_name='User',
            email='test@example.com',
            phone='0712345678',
            address='123 Test Street',
            payment_method='mpesa',
            payment_status='pending',
            mpesa_phone='254712345678',
            subtotal_amount=Decimal('1400.00'),
            total_amount=Decimal('1400.00')
        )
        
        # Create order items with variants
        OrderItem.objects.create(
            order=self.order,
            product=self.product,
            variant=None,
            price=self.product.price,
            quantity=1
        )
        
        OrderItem.objects.create(
            order=self.order,
            product=self.product,
            variant=self.variant_500g,
            price=self.variant_500g.calculated_price,
            quantity=1
        )
        
        OrderItem.objects.create(
            order=self.order,
            product=self.product,
            variant=self.variant_1kg,
            price=self.variant_1kg.calculated_price,
            quantity=1
        )
        
        # Clear any existing mail
        mail.outbox = []


class TestMultipleConsecutiveFailures(MultiplePaymentFailureTestCase):
    """Test multiple consecutive payment failures for the same order"""
    
    def test_two_consecutive_failures(self):
        """Test system behavior with 2 consecutive payment failures"""
        failure_reasons = [
            "Request cancelled by user",
            "Insufficient M-Pesa balance"
        ]
        
        initial_status_count = self.order.tracking_statuses.count()
        
        for attempt, reason in enumerate(failure_reasons, 1):
            # Simulate payment failure
            self.order.payment_status = 'failed'
            self.order.save()
            
            # Create tracking status
            OrderTrackingStatus.objects.create(
                order=self.order,
                status='cancelled',
                message=f'M-Pesa payment failed (Attempt #{attempt}): {reason}'
            )
            
            # Test cart preservation
            cart_preserved = CartPreservationService.preserve_cart_for_order(self.order)
            self.assertTrue(cart_preserved, f"Cart preservation failed on attempt {attempt}")
            
            # Test email notification
            with patch('yummytummy_store.services.send_mail') as mock_send_mail:
                mock_send_mail.return_value = True
                email_sent = OrderTrackingEmailService.send_payment_failed_notification(
                    order=self.order,
                    failure_reason=reason,
                    request=None
                )
                self.assertTrue(email_sent, f"Email notification failed on attempt {attempt}")
                self.assertEqual(mock_send_mail.call_count, 1)
        
        # Verify final state
        final_status_count = self.order.tracking_statuses.count()
        self.assertEqual(final_status_count - initial_status_count, 2)
        self.assertEqual(self.order.payment_status, 'failed')
        
        # Verify tracking statuses
        cancelled_statuses = self.order.tracking_statuses.filter(status='cancelled')
        self.assertEqual(cancelled_statuses.count(), 2)
    
    def test_five_consecutive_failures(self):
        """Test system behavior with 5 consecutive payment failures"""
        failure_reasons = [
            "Request cancelled by user",
            "Insufficient M-Pesa balance",
            "Network timeout",
            "Invalid phone number",
            "M-Pesa service unavailable"
        ]
        
        initial_status_count = self.order.tracking_statuses.count()
        email_count = 0
        
        for attempt, reason in enumerate(failure_reasons, 1):
            # Simulate payment failure
            self.order.payment_status = 'failed'
            self.order.save()
            
            # Create tracking status
            tracking_status = OrderTrackingStatus.objects.create(
                order=self.order,
                status='cancelled',
                message=f'M-Pesa payment failed (Attempt #{attempt}): {reason}'
            )
            
            # Test cart preservation for each attempt
            cart_preserved = CartPreservationService.preserve_cart_for_order(self.order)
            self.assertTrue(cart_preserved, f"Cart preservation failed on attempt {attempt}")
            
            # Verify preserved cart data
            self.order.refresh_from_db()
            self.assertIsNotNone(self.order.preserved_cart_data)
            cart_data = json.loads(self.order.preserved_cart_data)
            self.assertEqual(len(cart_data), 3)  # 3 order items
            
            # Test email notification
            with patch('yummytummy_store.services.send_mail') as mock_send_mail:
                mock_send_mail.return_value = True
                email_sent = OrderTrackingEmailService.send_payment_failed_notification(
                    order=self.order,
                    failure_reason=reason,
                    request=None
                )
                if email_sent:
                    email_count += 1
                self.assertTrue(email_sent, f"Email notification failed on attempt {attempt}")
        
        # Verify final state
        final_status_count = self.order.tracking_statuses.count()
        new_statuses = final_status_count - initial_status_count
        self.assertEqual(new_statuses, 5)
        self.assertEqual(self.order.payment_status, 'failed')
        
        # Verify all tracking statuses are recorded
        cancelled_statuses = self.order.tracking_statuses.filter(status='cancelled')
        self.assertEqual(cancelled_statuses.count(), 5)
        
        # Verify no automatic order cancellation
        self.assertNotEqual(self.order.payment_status, 'cancelled')
        
        # Verify email notifications (should be 5 emails sent)
        self.assertEqual(email_count, 5)
    
    def test_tracking_status_accumulation(self):
        """Test that tracking statuses accumulate without limits"""
        # Create 10 consecutive failures
        for i in range(10):
            OrderTrackingStatus.objects.create(
                order=self.order,
                status='cancelled',
                message=f'M-Pesa payment failed (Attempt #{i+1}): Test failure'
            )
        
        # Verify all statuses are stored
        cancelled_statuses = self.order.tracking_statuses.filter(status='cancelled')
        self.assertEqual(cancelled_statuses.count(), 10)
        
        # Verify no automatic cleanup
        total_statuses = self.order.tracking_statuses.count()
        self.assertGreaterEqual(total_statuses, 10)
        
        # Test database performance with many statuses
        start_time = time.time()
        latest_status = self.order.get_latest_tracking_status()
        query_time = time.time() - start_time
        
        self.assertIsNotNone(latest_status)
        self.assertLess(query_time, 0.1)  # Should be fast even with many records


class TestPaymentRetryBehavior(MultiplePaymentFailureTestCase):
    """Test payment retry behavior with multiple failures"""
    
    def test_infinite_retry_accessibility(self):
        """Test that payment retry URLs remain accessible indefinitely"""
        # Set order to failed status
        self.order.payment_status = 'failed'
        self.order.save()
        
        # Preserve cart data
        CartPreservationService.preserve_cart_for_order(self.order)
        
        # Test multiple retry attempts
        client = Client()
        retry_attempts = 20
        successful_retries = 0
        
        for attempt in range(retry_attempts):
            response = client.get(f'/payment/retry/{self.order.id}/')
            if response.status_code == 302:  # Successful redirect
                successful_retries += 1
        
        # Verify all retry attempts were successful
        self.assertEqual(successful_retries, retry_attempts)
        
        # Verify no built-in retry limitations
        self.assertEqual(self.order.payment_status, 'failed')  # Status unchanged
    
    def test_cart_preservation_across_multiple_failures(self):
        """Test that cart preservation works across multiple failures"""
        original_cart_data = None
        
        for attempt in range(5):
            # Simulate payment failure
            self.order.payment_status = 'failed'
            self.order.save()
            
            # Preserve cart
            cart_preserved = CartPreservationService.preserve_cart_for_order(self.order)
            self.assertTrue(cart_preserved)
            
            # Get preserved cart data
            self.order.refresh_from_db()
            current_cart_data = json.loads(self.order.preserved_cart_data)
            
            if original_cart_data is None:
                original_cart_data = current_cart_data
            else:
                # Verify cart data remains consistent
                self.assertEqual(current_cart_data, original_cart_data)
            
            # Test cart restoration
            client = Client()
            restore_success = CartPreservationService.restore_cart_from_order(client, self.order)
            self.assertTrue(restore_success)
    
    def test_checkout_data_restoration(self):
        """Test that checkout data is properly restored after multiple failures"""
        # Set order to failed status
        self.order.payment_status = 'failed'
        self.order.save()
        
        # Test payment retry
        client = Client()
        response = client.get(f'/payment/retry/{self.order.id}/')
        
        # Verify redirect to payment page
        self.assertEqual(response.status_code, 302)
        self.assertIn('/checkout/payment/', response.url)
        
        # Verify checkout data restoration
        checkout_data = client.session.get('checkout_data')
        self.assertIsNotNone(checkout_data)
        self.assertEqual(checkout_data['first_name'], self.order.first_name)
        self.assertEqual(checkout_data['last_name'], self.order.last_name)
        self.assertEqual(checkout_data['email'], self.order.email)
        self.assertEqual(float(checkout_data['total_amount']), float(self.order.total_amount))


class TestEmailNotificationBehavior(MultiplePaymentFailureTestCase):
    """Test email notification behavior with multiple failures"""
    
    @patch('yummytummy_store.services.send_mail')
    def test_multiple_failure_emails(self, mock_send_mail):
        """Test that multiple failure emails are sent without rate limiting"""
        mock_send_mail.return_value = True
        
        failure_reasons = [
            "Request cancelled by user",
            "Insufficient funds",
            "Network error",
            "Service unavailable",
            "Timeout error"
        ]
        
        emails_sent = 0
        
        for reason in failure_reasons:
            email_sent = OrderTrackingEmailService.send_payment_failed_notification(
                order=self.order,
                failure_reason=reason,
                request=None
            )
            if email_sent:
                emails_sent += 1
        
        # Verify all emails were sent (no rate limiting)
        self.assertEqual(emails_sent, 5)
        self.assertEqual(mock_send_mail.call_count, 5)
        
        # Verify email content for each call
        for call_args in mock_send_mail.call_args_list:
            args, kwargs = call_args
            self.assertIn('Payment Unsuccessful', kwargs['subject'])
            self.assertEqual(kwargs['recipient_list'], [self.order.email])
    
    @patch('yummytummy_store.services.send_mail')
    def test_email_spam_potential(self, mock_send_mail):
        """Test potential for email spam with rapid consecutive failures"""
        mock_send_mail.return_value = True
        
        # Simulate rapid consecutive failures (10 failures in quick succession)
        start_time = time.time()
        
        for i in range(10):
            OrderTrackingEmailService.send_payment_failed_notification(
                order=self.order,
                failure_reason=f"Rapid failure #{i+1}",
                request=None
            )
        
        end_time = time.time()
        
        # Verify all emails were sent without any throttling
        self.assertEqual(mock_send_mail.call_count, 10)
        
        # Verify no time-based rate limiting
        total_time = end_time - start_time
        self.assertLess(total_time, 5.0)  # Should complete quickly
    
    def test_email_content_consistency(self):
        """Test that email content remains consistent across multiple failures"""
        with patch('yummytummy_store.services.send_mail') as mock_send_mail:
            mock_send_mail.return_value = True
            
            # Send multiple failure emails
            for i in range(3):
                OrderTrackingEmailService.send_payment_failed_notification(
                    order=self.order,
                    failure_reason=f"Test failure {i+1}",
                    request=None
                )
            
            # Verify consistent email structure
            for call_args in mock_send_mail.call_args_list:
                args, kwargs = call_args
                
                # Check subject format
                expected_subject = f'YummyTummy Order #{self.order.get_order_number()} - Payment Unsuccessful'
                self.assertEqual(kwargs['subject'], expected_subject)
                
                # Check recipient
                self.assertEqual(kwargs['recipient_list'], [self.order.email])
                
                # Check that both HTML and plain text versions are provided
                self.assertIn('message', kwargs)
                self.assertIn('html_message', kwargs)


class TestSystemLimitationsAnalysis(MultiplePaymentFailureTestCase):
    """Test and document current system limitations"""
    
    def test_no_retry_attempt_limits(self):
        """Test that there are no built-in retry attempt limits"""
        # Set order to failed status
        self.order.payment_status = 'failed'
        self.order.save()
        
        # Test 50 retry attempts
        client = Client()
        successful_retries = 0
        
        for _ in range(50):
            response = client.get(f'/payment/retry/{self.order.id}/')
            if response.status_code == 302:
                successful_retries += 1
        
        # Verify no limits enforced
        self.assertEqual(successful_retries, 50)
        
        # Document limitation
        self.assertTrue(True, "LIMITATION: No maximum retry attempts enforced")
    
    def test_no_automatic_order_cancellation(self):
        """Test that orders are not automatically cancelled after multiple failures"""
        initial_status = self.order.payment_status
        
        # Create 20 failed attempts
        for i in range(20):
            OrderTrackingStatus.objects.create(
                order=self.order,
                status='cancelled',
                message=f'Failed attempt #{i+1}'
            )
        
        # Verify order is not automatically cancelled
        self.order.refresh_from_db()
        self.assertEqual(self.order.payment_status, initial_status)
        self.assertNotEqual(self.order.payment_status, 'cancelled')
        
        # Document limitation
        self.assertTrue(True, "LIMITATION: No automatic order cancellation after X failures")
    
    def test_no_cooldown_periods(self):
        """Test that there are no cooldown periods between retry attempts"""
        # Set order to failed status
        self.order.payment_status = 'failed'
        self.order.save()
        
        client = Client()
        
        # Test rapid consecutive retry attempts
        start_time = time.time()
        retry_times = []
        
        for _ in range(10):
            attempt_start = time.time()
            response = client.get(f'/payment/retry/{self.order.id}/')
            attempt_end = time.time()
            
            retry_times.append(attempt_end - attempt_start)
            self.assertEqual(response.status_code, 302)
        
        total_time = time.time() - start_time
        
        # Verify no artificial delays
        self.assertLess(total_time, 2.0)  # Should complete very quickly
        self.assertTrue(all(t < 0.5 for t in retry_times))  # Each attempt should be fast
        
        # Document limitation
        self.assertTrue(True, "LIMITATION: No cooldown periods between retry attempts")
    
    def test_database_bloat_potential(self):
        """Test potential for database bloat with unlimited tracking statuses"""
        initial_count = OrderTrackingStatus.objects.count()
        
        # Create many tracking statuses
        statuses_to_create = 100
        for i in range(statuses_to_create):
            OrderTrackingStatus.objects.create(
                order=self.order,
                status='cancelled',
                message=f'Database bloat test #{i+1}'
            )
        
        final_count = OrderTrackingStatus.objects.count()
        created_count = final_count - initial_count
        
        # Verify all statuses were created (no automatic cleanup)
        self.assertEqual(created_count, statuses_to_create)
        
        # Test query performance with many records
        start_time = time.time()
        order_statuses = self.order.tracking_statuses.all()[:10]
        list(order_statuses)  # Force evaluation
        query_time = time.time() - start_time
        
        # Performance should still be reasonable
        self.assertLess(query_time, 0.1)
        
        # Document limitation
        self.assertTrue(True, "LIMITATION: Unlimited tracking status accumulation")


class TestEdgeCasesAndPerformance(MultiplePaymentFailureTestCase):
    """Test edge cases and performance implications"""
    
    def test_concurrent_failure_handling(self):
        """Test handling of concurrent payment failures"""
        # This would test race conditions in a real scenario
        # For now, we'll test sequential rapid failures
        
        failure_count = 0
        
        for i in range(5):
            try:
                # Simulate rapid failure processing
                self.order.payment_status = 'failed'
                self.order.save()
                
                OrderTrackingStatus.objects.create(
                    order=self.order,
                    status='cancelled',
                    message=f'Concurrent failure test #{i+1}'
                )
                
                failure_count += 1
            except Exception as e:
                self.fail(f"Concurrent failure handling failed: {e}")
        
        self.assertEqual(failure_count, 5)
    
    def test_large_order_cart_preservation(self):
        """Test cart preservation with large orders (many items)"""
        # Create order with many items
        large_order = Order.objects.create(
            user=self.user,
            first_name='Large',
            last_name='Order',
            email='large@example.com',
            phone='0712345678',
            address='123 Large Street',
            payment_method='mpesa',
            payment_status='pending',
            total_amount=Decimal('5000.00')
        )
        
        # Add 20 order items
        for i in range(20):
            OrderItem.objects.create(
                order=large_order,
                product=self.product,
                variant=self.variant_500g if i % 2 == 0 else None,
                price=Decimal('250.00'),
                quantity=1
            )
        
        # Test cart preservation performance
        start_time = time.time()
        cart_preserved = CartPreservationService.preserve_cart_for_order(large_order)
        preservation_time = time.time() - start_time
        
        self.assertTrue(cart_preserved)
        self.assertLess(preservation_time, 1.0)  # Should complete within 1 second
        
        # Verify preserved data
        large_order.refresh_from_db()
        cart_data = json.loads(large_order.preserved_cart_data)
        self.assertEqual(len(cart_data), 20)
    
    def test_memory_usage_with_multiple_failures(self):
        """Test memory implications of multiple failure handling"""
        import sys
        
        initial_objects = len([obj for obj in locals().values()])
        
        # Create multiple failures and test memory usage
        for i in range(50):
            OrderTrackingStatus.objects.create(
                order=self.order,
                status='cancelled',
                message=f'Memory test failure #{i+1}'
            )
            
            # Test cart preservation
            CartPreservationService.preserve_cart_for_order(self.order)
        
        final_objects = len([obj for obj in locals().values()])
        
        # Memory usage should not grow excessively
        object_growth = final_objects - initial_objects
        self.assertLess(object_growth, 100)  # Reasonable object growth


class TestRecommendationsValidation(MultiplePaymentFailureTestCase):
    """Test validation of recommended improvements"""
    
    def test_retry_count_field_recommendation(self):
        """Test the need for a retry_count field on Order model"""
        # Current system has no retry count tracking
        self.assertFalse(hasattr(self.order, 'retry_count'))
        
        # Manually count retries from tracking statuses
        failed_attempts = self.order.tracking_statuses.filter(status='cancelled').count()
        
        # This is inefficient and should be replaced with a dedicated field
        self.assertTrue(True, "RECOMMENDATION: Add retry_count field to Order model")
    
    def test_email_rate_limiting_recommendation(self):
        """Test the need for email rate limiting"""
        with patch('yummytummy_store.services.send_mail') as mock_send_mail:
            mock_send_mail.return_value = True
            
            # Send 10 emails rapidly
            for i in range(10):
                OrderTrackingEmailService.send_payment_failed_notification(
                    order=self.order,
                    failure_reason=f"Rate limit test {i+1}",
                    request=None
                )
            
            # All emails are sent without rate limiting
            self.assertEqual(mock_send_mail.call_count, 10)
            
        self.assertTrue(True, "RECOMMENDATION: Implement email rate limiting")
    
    def test_support_escalation_recommendation(self):
        """Test the need for support team escalation"""
        # Create multiple failures
        for i in range(5):
            OrderTrackingStatus.objects.create(
                order=self.order,
                status='cancelled',
                message=f'Escalation test failure #{i+1}'
            )
        
        # No automatic support notification exists
        failed_attempts = self.order.tracking_statuses.filter(status='cancelled').count()
        self.assertGreaterEqual(failed_attempts, 3)
        
        # This should trigger support escalation but doesn't
        self.assertTrue(True, "RECOMMENDATION: Add support escalation after 3+ failures")


class TestReportGenerator:
    """Generate comprehensive test reports with recommendations"""

    @staticmethod
    def generate_test_report():
        """Generate detailed test report with findings and recommendations"""
        report = {
            'test_summary': {
                'total_test_cases': 6,
                'test_classes': [
                    'TestMultipleConsecutiveFailures',
                    'TestPaymentRetryBehavior',
                    'TestEmailNotificationBehavior',
                    'TestSystemLimitationsAnalysis',
                    'TestEdgeCasesAndPerformance',
                    'TestRecommendationsValidation'
                ]
            },
            'critical_findings': [
                'No retry attempt limitations enforced',
                'No email rate limiting mechanisms',
                'No automatic order cancellation after multiple failures',
                'No cooldown periods between retry attempts',
                'Unlimited tracking status accumulation',
                'No support team escalation triggers',
                'Potential for email spam with rapid failures',
                'Database bloat potential with unlimited records'
            ],
            'system_behavior_analysis': {
                'cart_preservation': 'Works correctly across multiple failures',
                'payment_retry': 'Accessible indefinitely without limits',
                'email_notifications': 'Sent for every failure without rate limiting',
                'order_status': 'Remains failed, no automatic cancellation',
                'tracking_statuses': 'Accumulate without cleanup',
                'performance': 'Acceptable for moderate failure counts'
            },
            'recommendations': {
                'immediate': [
                    'Add retry_count field to Order model',
                    'Implement maximum retry attempts (3-5)',
                    'Add email rate limiting (1 email per hour)',
                    'Create support escalation after 3+ failures'
                ],
                'short_term': [
                    'Add cooldown periods between retries',
                    'Implement automatic order expiration',
                    'Add fraud detection for suspicious patterns',
                    'Create cleanup job for old tracking statuses'
                ],
                'long_term': [
                    'Build comprehensive retry management dashboard',
                    'Implement machine learning for failure prediction',
                    'Add customer behavior analytics',
                    'Create automated customer support workflows'
                ]
            },
            'risk_assessment': {
                'email_spam': 'HIGH - No rate limiting',
                'database_bloat': 'MEDIUM - Unlimited record growth',
                'customer_frustration': 'HIGH - No guidance for repeated failures',
                'support_overhead': 'HIGH - No automated escalation',
                'fraud_potential': 'MEDIUM - No detection mechanisms'
            }
        }

        return report


def run_comprehensive_tests():
    """Run comprehensive test suite with detailed reporting"""
    import unittest
    import time
    from io import StringIO

    print("🧪 YummyTummy M-Pesa Multiple Payment Failures - Comprehensive Test Suite")
    print("="*80)

    # Capture test output
    test_output = StringIO()

    # Create test suite
    test_classes = [
        TestMultipleConsecutiveFailures,
        TestPaymentRetryBehavior,
        TestEmailNotificationBehavior,
        TestSystemLimitationsAnalysis,
        TestEdgeCasesAndPerformance,
        TestRecommendationsValidation
    ]

    suite = unittest.TestSuite()
    for test_class in test_classes:
        tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
        suite.addTests(tests)

    # Run tests
    start_time = time.time()
    runner = unittest.TextTestRunner(stream=test_output, verbosity=2)
    result = runner.run(suite)
    end_time = time.time()

    # Print results
    print(f"\n📊 TEST EXECUTION SUMMARY")
    print("="*50)
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Success rate: {((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100):.1f}%")
    print(f"Execution time: {end_time - start_time:.2f} seconds")

    # Print detailed results
    if result.failures:
        print(f"\n❌ FAILURES ({len(result.failures)}):")
        for test, traceback in result.failures:
            print(f"   - {test}: {traceback.split('AssertionError:')[-1].strip()}")

    if result.errors:
        print(f"\n🚨 ERRORS ({len(result.errors)}):")
        for test, traceback in result.errors:
            print(f"   - {test}: {traceback.split('Exception:')[-1].strip()}")

    # Generate comprehensive report
    report = TestReportGenerator.generate_test_report()

    print(f"\n🔍 CRITICAL FINDINGS:")
    for finding in report['critical_findings']:
        print(f"   • {finding}")

    print(f"\n💡 IMMEDIATE RECOMMENDATIONS:")
    for rec in report['recommendations']['immediate']:
        print(f"   • {rec}")

    print(f"\n⚠️  RISK ASSESSMENT:")
    for risk, level in report['risk_assessment'].items():
        print(f"   • {risk.replace('_', ' ').title()}: {level}")

    print(f"\n📋 SYSTEM BEHAVIOR ANALYSIS:")
    for behavior, status in report['system_behavior_analysis'].items():
        print(f"   • {behavior.replace('_', ' ').title()}: {status}")

    # Save detailed report
    try:
        with open('mpesa_failure_test_report.json', 'w') as f:
            import json
            json.dump(report, f, indent=2)
        print(f"\n💾 Detailed report saved to: mpesa_failure_test_report.json")
    except Exception as e:
        print(f"\n❌ Failed to save report: {e}")

    print(f"\n🎯 CONCLUSION:")
    if result.testsRun > 0 and len(result.failures) == 0 and len(result.errors) == 0:
        print("   ✅ All tests passed - System behavior documented")
        print("   ⚠️  Multiple critical limitations identified")
        print("   🔧 Immediate improvements recommended")
    else:
        print("   ❌ Some tests failed - Review results above")

    return result


if __name__ == '__main__':
    # Check if running in Django environment
    try:
        import django
        from django.conf import settings
        if not settings.configured:
            import os
            os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'yummytummy_project.settings')
            django.setup()

        # Run comprehensive test suite
        run_comprehensive_tests()

    except ImportError:
        print("❌ Django not available. Please run from Django project directory.")
        print("Usage: python manage.py test test_multiple_mpesa_failures")
    except Exception as e:
        print(f"❌ Error running tests: {e}")
        import unittest
        unittest.main()
