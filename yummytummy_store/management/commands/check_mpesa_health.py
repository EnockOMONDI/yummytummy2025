"""
Django management command to check M-Pesa API health and send alerts if issues are detected.

Usage:
    python manage.py check_mpesa_health
    
This command can be run periodically via cron to monitor M-Pesa service health.
"""

from django.core.management.base import BaseCommand
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from yummytummy_store.mpesa_service import MPesaService
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Check M-Pesa API health and send alerts if issues detected'

    def add_arguments(self, parser):
        parser.add_argument(
            '--send-alerts',
            action='store_true',
            help='Send email alerts if issues are detected',
        )
        parser.add_argument(
            '--test-stk-push',
            action='store_true',
            help='Test STK Push functionality (use with caution)',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('🔍 Starting M-Pesa Health Check...'))
        
        health_status = {
            'authentication': False,
            'stk_push': False,
            'overall': False,
            'errors': []
        }
        
        # Test authentication
        try:
            mpesa_service = MPesaService()
            access_token = mpesa_service.get_access_token()
            
            if access_token:
                health_status['authentication'] = True
                self.stdout.write(self.style.SUCCESS('✅ M-Pesa Authentication: PASS'))
            else:
                health_status['errors'].append('M-Pesa authentication failed - no access token received')
                self.stdout.write(self.style.ERROR('❌ M-Pesa Authentication: FAIL'))
                
        except Exception as e:
            health_status['errors'].append(f'M-Pesa authentication error: {str(e)}')
            self.stdout.write(self.style.ERROR(f'❌ M-Pesa Authentication: ERROR - {str(e)}'))
        
        # Test STK Push if requested (optional due to potential charges)
        if options['test_stk_push'] and health_status['authentication']:
            try:
                # Use minimal test amount and test phone number
                response = mpesa_service.initiate_stk_push(
                    phone_number='254708374149',  # Safaricom test number
                    amount=1.0,  # Minimal amount
                    order_id=99999,  # Test order ID
                    callback_url='https://webhook.site/test-callback'
                )
                
                if response.get('success'):
                    health_status['stk_push'] = True
                    self.stdout.write(self.style.SUCCESS('✅ M-Pesa STK Push: PASS'))
                else:
                    error_msg = response.get('error', 'Unknown error')
                    health_status['errors'].append(f'STK Push failed: {error_msg}')
                    self.stdout.write(self.style.ERROR(f'❌ M-Pesa STK Push: FAIL - {error_msg}'))
                    
            except Exception as e:
                health_status['errors'].append(f'STK Push test error: {str(e)}')
                self.stdout.write(self.style.ERROR(f'❌ M-Pesa STK Push: ERROR - {str(e)}'))
        else:
            self.stdout.write(self.style.WARNING('⚠️  STK Push test skipped (use --test-stk-push to enable)'))
        
        # Determine overall health
        if options['test_stk_push']:
            health_status['overall'] = health_status['authentication'] and health_status['stk_push']
        else:
            health_status['overall'] = health_status['authentication']
        
        # Display summary
        if health_status['overall']:
            self.stdout.write(self.style.SUCCESS('\n🎉 M-Pesa Health Check: HEALTHY'))
        else:
            self.stdout.write(self.style.ERROR('\n🚨 M-Pesa Health Check: UNHEALTHY'))
            for error in health_status['errors']:
                self.stdout.write(self.style.ERROR(f'   • {error}'))
        
        # Send alerts if requested and issues detected
        if options['send_alerts'] and not health_status['overall']:
            self.send_health_alert(health_status)

        # Django management commands should not return values
        # Exit code is handled by Django automatically based on exceptions

    def send_health_alert(self, health_status):
        """Send email alert about M-Pesa health issues"""
        try:
            subject = '🚨 YummyTummy M-Pesa Service Alert'
            
            message = f"""
M-Pesa Health Check Failed

Status Summary:
- Authentication: {'✅ PASS' if health_status['authentication'] else '❌ FAIL'}
- STK Push: {'✅ PASS' if health_status['stk_push'] else '❌ FAIL'}
- Overall: {'✅ HEALTHY' if health_status['overall'] else '❌ UNHEALTHY'}

Errors Detected:
"""
            for error in health_status['errors']:
                message += f"• {error}\n"
            
            message += f"""

Recommended Actions:
1. Check M-Pesa credentials and configuration
2. Verify network connectivity to Safaricom APIs
3. Contact Safaricom support if authentication issues persist
4. Review application logs for detailed error information

Time: {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}
Environment: {settings.MPESA_ENVIRONMENT}
"""
            
            # Send to admin email
            admin_email = getattr(settings, 'ADMIN_EMAIL', 'admin@yummytummy.com')
            
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[admin_email],
                fail_silently=False,
            )
            
            self.stdout.write(self.style.SUCCESS(f'📧 Alert email sent to {admin_email}'))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Failed to send alert email: {str(e)}'))


# Example cron job setup:
# Add to crontab to run every 15 minutes:
# */15 * * * * cd /path/to/project && python manage.py check_mpesa_health --send-alerts

# Example usage:
# python manage.py check_mpesa_health                    # Basic health check
# python manage.py check_mpesa_health --send-alerts     # With email alerts
# python manage.py check_mpesa_health --test-stk-push   # Include STK Push test
