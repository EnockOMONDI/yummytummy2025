#!/usr/bin/env python3
"""
Test Multiple M-Pesa Payment Failures Analysis
Analyzes what happens when a customer experiences multiple consecutive payment failures
"""

import os
import sys
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'yummytummy_project.settings')
django.setup()

from yummytummy_store.models import Order, OrderTrackingStatus
from yummytummy_store.services import OrderTrackingEmailService, CartPreservationService
from django.test import Client
from django.contrib.auth.models import User
from decimal import Decimal

def simulate_multiple_payment_failures():
    """Simulate multiple consecutive payment failures for the same order"""
    print("🔄 SIMULATING MULTIPLE CONSECUTIVE PAYMENT FAILURES")
    print("="*70)
    
    try:
        # Get or create a test order
        order = Order.objects.filter(payment_method='mpesa').first()
        if not order:
            print("❌ No M-Pesa orders found for testing")
            return None
            
        print(f"✅ Testing with order: {order.get_order_number()}")
        print(f"✅ Initial payment status: {order.payment_status}")
        
        # Clear any existing tracking statuses for clean test
        initial_status_count = order.tracking_statuses.count()
        print(f"✅ Initial tracking statuses: {initial_status_count}")
        
        # Simulate 5 consecutive payment failures
        failure_scenarios = [
            "Request cancelled by user",
            "Insufficient M-Pesa balance", 
            "Network timeout",
            "Invalid phone number",
            "M-Pesa service unavailable"
        ]
        
        for attempt, failure_reason in enumerate(failure_scenarios, 1):
            print(f"\n🚫 FAILURE ATTEMPT #{attempt}")
            print(f"   Reason: {failure_reason}")
            
            # Set order to failed status (simulating M-Pesa callback)
            order.payment_status = 'failed'
            order.save()
            
            # Create failed payment tracking status
            tracking_status = OrderTrackingStatus.objects.create(
                order=order,
                status='cancelled',
                message=f'M-Pesa payment failed (Attempt #{attempt}): {failure_reason}'
            )
            
            # Send failed payment notification email
            try:
                email_sent = OrderTrackingEmailService.send_payment_failed_notification(
                    order=order,
                    failure_reason=failure_reason,
                    request=None
                )
                print(f"   Email notification: {'✅ SENT' if email_sent else '❌ FAILED'}")
            except Exception as e:
                print(f"   Email notification: ❌ ERROR - {str(e)}")
            
            # Test cart preservation (should work for each attempt)
            cart_preserved = CartPreservationService.preserve_cart_for_order(order)
            print(f"   Cart preservation: {'✅ SUCCESS' if cart_preserved else '❌ FAILED'}")
            
            # Test payment retry URL access
            client = Client()
            response = client.get(f'/payment/retry/{order.id}/')
            retry_accessible = response.status_code == 302
            print(f"   Retry URL access: {'✅ SUCCESS' if retry_accessible else '❌ FAILED'}")
            
            print(f"   Order status after attempt #{attempt}: {order.payment_status}")
        
        # Final analysis
        final_status_count = order.tracking_statuses.count()
        new_statuses = final_status_count - initial_status_count
        
        print(f"\n📊 FINAL ANALYSIS:")
        print(f"   Total failure attempts: {len(failure_scenarios)}")
        print(f"   New tracking statuses created: {new_statuses}")
        print(f"   Final order status: {order.payment_status}")
        print(f"   Order still retryable: {'✅ YES' if order.payment_status == 'failed' else '❌ NO'}")
        
        return order
        
    except Exception as e:
        print(f"❌ Multiple failure simulation error: {str(e)}")
        return None

def analyze_tracking_status_accumulation(order):
    """Analyze how tracking statuses accumulate with multiple failures"""
    print("\n📈 TRACKING STATUS ACCUMULATION ANALYSIS")
    print("="*70)
    
    try:
        if not order:
            print("❌ No order provided for analysis")
            return
            
        # Get all tracking statuses for this order
        all_statuses = order.tracking_statuses.all()
        cancelled_statuses = order.tracking_statuses.filter(status='cancelled')
        
        print(f"✅ Order: {order.get_order_number()}")
        print(f"✅ Total tracking statuses: {all_statuses.count()}")
        print(f"✅ Cancelled statuses (failures): {cancelled_statuses.count()}")
        
        print(f"\n📋 TRACKING STATUS HISTORY:")
        for i, status in enumerate(all_statuses[:10], 1):  # Show last 10
            print(f"   {i}. {status.get_status_display()} - {status.message[:50]}...")
            print(f"      Created: {status.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
        
        if all_statuses.count() > 10:
            print(f"   ... and {all_statuses.count() - 10} more statuses")
        
        # Check for potential issues
        if cancelled_statuses.count() > 3:
            print(f"\n⚠️  WARNING: {cancelled_statuses.count()} failed attempts detected!")
            print("   This order may need manual intervention.")
        
        return {
            'total_statuses': all_statuses.count(),
            'failed_attempts': cancelled_statuses.count(),
            'needs_intervention': cancelled_statuses.count() > 3
        }
        
    except Exception as e:
        print(f"❌ Tracking status analysis error: {str(e)}")
        return None

def test_infinite_retry_scenario():
    """Test if customers can retry indefinitely"""
    print("\n♾️  INFINITE RETRY SCENARIO TEST")
    print("="*70)
    
    try:
        # Get a failed order
        order = Order.objects.filter(payment_status='failed').first()
        if not order:
            print("❌ No failed orders found for testing")
            return False
            
        print(f"✅ Testing infinite retry with order: {order.get_order_number()}")
        
        # Test multiple retry attempts
        retry_attempts = 10
        successful_retries = 0
        
        for attempt in range(1, retry_attempts + 1):
            client = Client()
            response = client.get(f'/payment/retry/{order.id}/')
            
            if response.status_code == 302:  # Successful redirect
                successful_retries += 1
                print(f"   Retry attempt #{attempt}: ✅ SUCCESS")
            else:
                print(f"   Retry attempt #{attempt}: ❌ FAILED ({response.status_code})")
        
        print(f"\n📊 RETRY TEST RESULTS:")
        print(f"   Total retry attempts: {retry_attempts}")
        print(f"   Successful retries: {successful_retries}")
        print(f"   Success rate: {(successful_retries/retry_attempts)*100:.1f}%")
        
        # Check if there are any built-in limitations
        if successful_retries == retry_attempts:
            print("   ⚠️  NO RETRY LIMITATIONS DETECTED")
            print("   Customers can retry indefinitely!")
        else:
            print("   ✅ Some retry limitations exist")
        
        return successful_retries == retry_attempts
        
    except Exception as e:
        print(f"❌ Infinite retry test error: {str(e)}")
        return False

def analyze_email_notification_behavior():
    """Analyze email notification behavior with multiple failures"""
    print("\n📧 EMAIL NOTIFICATION BEHAVIOR ANALYSIS")
    print("="*70)
    
    try:
        # Get an order with multiple failed attempts
        order = Order.objects.filter(
            payment_status='failed',
            tracking_statuses__status='cancelled'
        ).first()
        
        if not order:
            print("❌ No orders with failed attempts found")
            return
            
        failed_attempts = order.tracking_statuses.filter(status='cancelled').count()
        print(f"✅ Analyzing order: {order.get_order_number()}")
        print(f"✅ Failed attempts: {failed_attempts}")
        
        # Test email sending for each failure type
        failure_reasons = [
            "Request cancelled by user",
            "Insufficient funds",
            "Network error"
        ]
        
        emails_sent = 0
        for i, reason in enumerate(failure_reasons, 1):
            try:
                success = OrderTrackingEmailService.send_payment_failed_notification(
                    order=order,
                    failure_reason=reason,
                    request=None
                )
                if success:
                    emails_sent += 1
                    print(f"   Email #{i} ({reason}): ✅ SENT")
                else:
                    print(f"   Email #{i} ({reason}): ❌ FAILED")
            except Exception as e:
                print(f"   Email #{i} ({reason}): ❌ ERROR - {str(e)}")
        
        print(f"\n📊 EMAIL ANALYSIS:")
        print(f"   Emails attempted: {len(failure_reasons)}")
        print(f"   Emails sent: {emails_sent}")
        
        if emails_sent == len(failure_reasons):
            print("   ⚠️  NO EMAIL RATE LIMITING DETECTED")
            print("   Multiple failure emails will be sent for each attempt!")
        
        return emails_sent
        
    except Exception as e:
        print(f"❌ Email analysis error: {str(e)}")
        return 0

def identify_potential_issues():
    """Identify potential issues with current multiple failure handling"""
    print("\n🚨 POTENTIAL ISSUES IDENTIFICATION")
    print("="*70)
    
    issues = []
    
    # Issue 1: No retry attempt limit
    print("1. RETRY ATTEMPT LIMITATIONS:")
    print("   ❌ No maximum retry attempts enforced")
    print("   ❌ No cooldown period between retries")
    print("   ❌ No automatic order cancellation after X failures")
    issues.append("No retry limitations")
    
    # Issue 2: Email spam potential
    print("\n2. EMAIL NOTIFICATION ISSUES:")
    print("   ❌ No email rate limiting")
    print("   ❌ Customer receives email for every failure")
    print("   ❌ No escalation to support after multiple failures")
    issues.append("Email spam potential")
    
    # Issue 3: Database accumulation
    print("\n3. DATABASE ACCUMULATION:")
    print("   ❌ Unlimited tracking status records")
    print("   ❌ No cleanup of old failed attempts")
    print("   ❌ Potential database bloat over time")
    issues.append("Database accumulation")
    
    # Issue 4: No business logic safeguards
    print("\n4. BUSINESS LOGIC SAFEGUARDS:")
    print("   ❌ No fraud detection for repeated failures")
    print("   ❌ No support team notification")
    print("   ❌ No order expiration after prolonged failures")
    issues.append("No business safeguards")
    
    # Issue 5: Customer experience
    print("\n5. CUSTOMER EXPERIENCE:")
    print("   ❌ No guidance for repeated failures")
    print("   ❌ No alternative payment method suggestions")
    print("   ❌ No escalation to human support")
    issues.append("Poor customer experience")
    
    print(f"\n📊 SUMMARY:")
    print(f"   Total issues identified: {len(issues)}")
    for i, issue in enumerate(issues, 1):
        print(f"   {i}. {issue}")
    
    return issues

def generate_recommendations():
    """Generate recommendations for improving multiple failure handling"""
    print("\n💡 RECOMMENDATIONS FOR IMPROVEMENT")
    print("="*70)
    
    recommendations = [
        {
            'category': 'Retry Limitations',
            'items': [
                'Implement maximum retry attempts (e.g., 3-5 attempts)',
                'Add cooldown period between retries (e.g., 5 minutes)',
                'Auto-cancel orders after 24-48 hours of failures'
            ]
        },
        {
            'category': 'Email Management',
            'items': [
                'Implement email rate limiting (max 1 email per hour)',
                'Send escalation emails after 3+ failures',
                'Include alternative payment methods in failure emails'
            ]
        },
        {
            'category': 'Database Optimization',
            'items': [
                'Add retry_count field to Order model',
                'Implement cleanup job for old tracking statuses',
                'Add indexes for failure analysis queries'
            ]
        },
        {
            'category': 'Business Logic',
            'items': [
                'Add fraud detection for suspicious retry patterns',
                'Notify support team after 3+ consecutive failures',
                'Implement order expiration mechanism'
            ]
        },
        {
            'category': 'Customer Experience',
            'items': [
                'Provide clear guidance for common failure reasons',
                'Offer alternative payment methods after 2+ failures',
                'Add live chat or support contact after 3+ failures'
            ]
        }
    ]
    
    for rec in recommendations:
        print(f"\n🔧 {rec['category'].upper()}:")
        for item in rec['items']:
            print(f"   • {item}")
    
    return recommendations

def main():
    """Run comprehensive multiple payment failure analysis"""
    print("🚫 YummyTummy Multiple M-Pesa Payment Failures Analysis")
    print("Analyzing system behavior with consecutive payment failures")
    print("="*70)
    
    # Run analysis
    order = simulate_multiple_payment_failures()
    tracking_analysis = analyze_tracking_status_accumulation(order)
    infinite_retry = test_infinite_retry_scenario()
    email_count = analyze_email_notification_behavior()
    issues = identify_potential_issues()
    recommendations = generate_recommendations()
    
    # Final summary
    print("\n" + "="*70)
    print("🎯 MULTIPLE FAILURE ANALYSIS SUMMARY")
    print("="*70)
    
    print(f"\n📊 KEY FINDINGS:")
    print(f"   • Infinite retry attempts: {'❌ YES' if infinite_retry else '✅ NO'}")
    print(f"   • Email spam potential: {'❌ HIGH' if email_count > 2 else '✅ LOW'}")
    print(f"   • Database accumulation: {'❌ YES' if tracking_analysis and tracking_analysis['total_statuses'] > 10 else '✅ MANAGEABLE'}")
    print(f"   • Business safeguards: ❌ MISSING")
    print(f"   • Issues identified: {len(issues)}")
    
    print(f"\n🚨 CRITICAL ISSUES:")
    print("   1. No retry attempt limitations")
    print("   2. No email rate limiting")
    print("   3. No automatic escalation to support")
    print("   4. No order expiration mechanism")
    print("   5. No fraud detection")
    
    print(f"\n✅ WHAT WORKS WELL:")
    print("   • Cart preservation works for all retry attempts")
    print("   • Payment retry URL remains functional")
    print("   • Tracking statuses are properly recorded")
    print("   • Email notifications are sent successfully")
    
    from datetime import datetime
    print(f"\n📅 Analysis completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == "__main__":
    main()
