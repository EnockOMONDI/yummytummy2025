"""
Email and order tracking services for YummyTummy store.
Handles automatic account creation and order tracking emails.
"""

import json
import secrets
import string
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils import timezone
from .models import Order, AutoCreatedAccount, OrderTrackingStatus


class OrderTrackingEmailService:
    """Service for handling order tracking emails and account creation"""
    
    @staticmethod
    def generate_secure_password(length=12):
        """Generate a secure random password"""
        # Use a mix of letters, digits, and safe special characters
        characters = string.ascii_letters + string.digits + "!@#$%^&*"
        password = ''.join(secrets.choice(characters) for _ in range(length))
        
        # Ensure password has at least one uppercase, lowercase, digit, and special char
        if (any(c.islower() for c in password) and 
            any(c.isupper() for c in password) and 
            any(c.isdigit() for c in password) and 
            any(c in "!@#$%^&*" for c in password)):
            return password
        else:
            # Regenerate if criteria not met
            return OrderTrackingEmailService.generate_secure_password(length)
    
    @staticmethod
    def create_user_account(order_data):
        """Create a user account from order data"""
        email = order_data['email']
        first_name = order_data['first_name']
        last_name = order_data['last_name']
        
        # Check if user already exists
        existing_user = User.objects.filter(email=email).first()
        if existing_user:
            return existing_user, None  # Return existing user, no password
        
        # Generate secure password
        temp_password = OrderTrackingEmailService.generate_secure_password()
        
        # Create new user
        user = User.objects.create_user(
            username=email,  # Use email as username
            email=email,
            first_name=first_name,
            last_name=last_name,
            password=temp_password
        )
        
        return user, temp_password
    
    @staticmethod
    def create_auto_account_record(user, order, temp_password):
        """Create AutoCreatedAccount record for tracking"""
        auto_account = AutoCreatedAccount.objects.create(
            user=user,
            created_during_order=order,
            initial_password_sent=False
        )
        
        # Generate first login token
        auto_account.generate_first_login_token()
        
        return auto_account
    
    @staticmethod
    def format_order_items_for_email(order):
        """Format order items with variant information for email display"""
        items = []
        for item in order.items.all():
            item_data = {
                'name': item.product.name,
                'variant_name': item.variant.name if item.variant else None,
                'quantity': item.quantity,
                'price': item.price,
                'total': item.get_cost(),
                'formatted_price': item.get_formatted_price(),
                'formatted_total': item.get_formatted_cost(),
            }
            
            # Create display name with variant
            if item.variant:
                item_data['display_name'] = f"{item.product.name} - {item.variant.name}"
            else:
                item_data['display_name'] = item.product.name
                
            items.append(item_data)
        
        return items
    
    @staticmethod
    def get_first_login_url(auto_account, request=None):
        """Generate first-time login URL with token"""
        if request:
            domain = request.get_host()
            protocol = 'https' if request.is_secure() else 'http'
        else:
            # Use SITE_URL from settings (configured for production domain)
            site_url = getattr(settings, 'SITE_URL', 'https://livegreat.co.ke')
            # Extract domain and protocol from SITE_URL
            if site_url.startswith('https://'):
                protocol = 'https'
                domain = site_url[8:]  # Remove 'https://'
            elif site_url.startswith('http://'):
                protocol = 'http'
                domain = site_url[7:]  # Remove 'http://'
            else:
                protocol = 'https'
                domain = site_url

        login_path = reverse('yummytummy_store:first_time_login', args=[auto_account.first_login_token])
        return f"{protocol}://{domain}{login_path}"
    
    @staticmethod
    def send_order_confirmation_with_account(order, user, temp_password, auto_account, request=None):
        """Send order confirmation email with account creation details"""
        
        # Format order items
        order_items = OrderTrackingEmailService.format_order_items_for_email(order)
        
        # Generate login URL
        login_url = OrderTrackingEmailService.get_first_login_url(auto_account, request)
        
        # Prepare email context
        context = {
            'order': order,
            'user': user,
            'temp_password': temp_password,
            'login_url': login_url,
            'order_items': order_items,
            'order_number': order.get_order_number(),
            'customer_name': order.get_customer_name(),
            'site_name': 'YummyTummy',
            'support_email': getattr(settings, 'DEFAULT_FROM_EMAIL', 'support@yummytummy.com'),
            'token_expires_days': 7,
        }
        
        # Render email templates
        subject = f'YummyTummy Order #{order.get_order_number()} - Order Confirmation & Tracking'
        html_message = render_to_string('yummytummy_store/emails/order_confirmation_with_account.html', context)
        plain_message = strip_tags(html_message)
        
        # Send email
        try:
            send_mail(
                subject=subject,
                message=plain_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                html_message=html_message,
                fail_silently=False,
            )
            
            # Mark email as sent
            auto_account.initial_password_sent = True
            auto_account.save()
            
            order.account_creation_email_sent = True
            order.save()
            
            return True
            
        except Exception as e:
            # Log error (in production, use proper logging)
            print(f"Failed to send order confirmation email: {e}")
            return False
    
    @staticmethod
    def send_regular_order_confirmation(order, request=None):
        """Send regular order confirmation email (for existing users or guest orders)"""
        
        # Format order items
        order_items = OrderTrackingEmailService.format_order_items_for_email(order)
        
        # Prepare email context
        context = {
            'order': order,
            'order_items': order_items,
            'order_number': order.get_order_number(),
            'customer_name': order.get_customer_name(),
            'site_name': 'YummyTummy',
            'support_email': getattr(settings, 'DEFAULT_FROM_EMAIL', 'support@yummytummy.com'),
        }
        
        # Add login URL if user has account
        if order.user:
            if request:
                domain = request.get_host()
                protocol = 'https' if request.is_secure() else 'http'
            else:
                # Use SITE_URL from settings (configured for production domain)
                site_url = getattr(settings, 'SITE_URL', 'https://livegreat.co.ke')
                # Extract domain and protocol from SITE_URL
                if site_url.startswith('https://'):
                    protocol = 'https'
                    domain = site_url[8:]  # Remove 'https://'
                elif site_url.startswith('http://'):
                    protocol = 'http'
                    domain = site_url[7:]  # Remove 'http://'
                else:
                    protocol = 'https'
                    domain = site_url

            login_path = reverse('yummytummy_store:order_tracking_dashboard')
            context['login_url'] = f"{protocol}://{domain}{login_path}"
        
        # Render email templates
        subject = f'YummyTummy Order #{order.get_order_number()} - Confirmation'
        
        if order.user:
            template = 'yummytummy_store/emails/order_confirmation_user.html'
        else:
            template = 'yummytummy_store/emails/order_confirmation_guest.html'
            
        html_message = render_to_string(template, context)
        plain_message = strip_tags(html_message)
        
        # Send email
        try:
            send_mail(
                subject=subject,
                message=plain_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[order.email],
                html_message=html_message,
                fail_silently=False,
            )
            return True
            
        except Exception as e:
            # Log error (in production, use proper logging)
            print(f"Failed to send order confirmation email: {e}")
            return False

    @staticmethod
    def send_payment_confirmation_email(order, request=None):
        """Send email after payment is confirmed (for auto-created accounts)"""
        try:
            # Get auto account details
            auto_account = AutoCreatedAccount.objects.get(created_during_order=order)

            # Format order items
            order_items = OrderTrackingEmailService.format_order_items_for_email(order)

            # Generate login URL
            login_url = OrderTrackingEmailService.get_first_login_url(auto_account, request)

            # Prepare email context
            context = {
                'order': order,
                'user': order.user,
                'login_url': login_url,
                'order_items': order_items,
                'order_number': order.get_order_number(),
                'customer_name': order.get_customer_name(),
                'site_name': 'YummyTummy',
                'support_email': getattr(settings, 'DEFAULT_FROM_EMAIL', 'support@yummytummy.com'),
                'token_expires_days': 7,
            }

            # Render email content
            html_message = render_to_string('yummytummy_store/emails/payment_confirmation_with_account.html', context)
            plain_message = strip_tags(html_message)

            # Send email
            send_mail(
                subject=f'YummyTummy Order #{order.get_order_number()} - Payment Confirmed & Account Ready',
                message=plain_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[order.user.email],
                html_message=html_message,
                fail_silently=False,
            )

            return True

        except Exception as e:
            # Log error (in production, use proper logging)
            print(f"Failed to send payment confirmation email: {e}")
            return False

    @staticmethod
    def send_status_update_email(order, tracking_status, request=None):
        """Send email notification when order status is updated"""
        try:
            # Format order items
            order_items = OrderTrackingEmailService.format_order_items_for_email(order)

            # Prepare email context
            context = {
                'order': order,
                'tracking_status': tracking_status,
                'order_items': order_items,
                'order_number': order.get_order_number(),
                'customer_name': order.get_customer_name(),
                'site_name': 'YummyTummy',
                'support_email': getattr(settings, 'DEFAULT_FROM_EMAIL', 'support@yummytummy.com'),
            }

            # Render email content
            html_message = render_to_string('yummytummy_store/emails/order_status_update.html', context)
            plain_message = strip_tags(html_message)

            # Send email
            send_mail(
                subject=f'YummyTummy Order #{order.get_order_number()} - Status Update: {tracking_status.get_status_display()}',
                message=plain_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[order.email],
                html_message=html_message,
                fail_silently=False,
            )

            return True

        except Exception as e:
            # Log error (in production, use proper logging)
            print(f"Failed to send status update email: {e}")
            return False

    @staticmethod
    def send_payment_failed_notification(order, failure_reason=None, request=None):
        """Send email notification when M-Pesa payment fails"""
        try:
            # Format order items
            order_items = OrderTrackingEmailService.format_order_items_for_email(order)

            # Generate retry payment URL (preserve cart for retry)
            if request:
                retry_payment_url = request.build_absolute_uri(reverse('yummytummy_store:payment_retry', kwargs={'order_id': order.id}))
                track_order_url = request.build_absolute_uri(reverse('yummytummy_store:guest_order_tracking'))
            else:
                # Fallback URLs for callback context
                retry_payment_url = f"https://yummytummy.com/payment/retry/{order.id}/"
                track_order_url = "https://yummytummy.com/track-order/"

            # Prepare email context
            context = {
                'order': order,
                'order_items': order_items,
                'order_number': order.get_order_number(),
                'customer_name': order.get_customer_name(),
                'failure_reason': failure_reason,
                'retry_payment_url': retry_payment_url,
                'track_order_url': track_order_url,
                'site_name': 'YummyTummy',
                'support_email': getattr(settings, 'DEFAULT_FROM_EMAIL', 'support@yummytummy.com'),
            }

            # Render email content
            html_message = render_to_string('yummytummy_store/emails/payment_failed_notification.html', context)
            plain_message = render_to_string('yummytummy_store/emails/payment_failed_notification.txt', context)

            # Send email
            send_mail(
                subject=f'YummyTummy Order #{order.get_order_number()} - Payment Unsuccessful',
                message=plain_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[order.email],
                html_message=html_message,
                fail_silently=False,
            )

            return True

        except Exception as e:
            # Log error (in production, use proper logging)
            print(f"Failed to send payment failed notification: {e}")
            return False


class CartPreservationService:
    """Service for preserving cart contents during payment failures"""

    @staticmethod
    def preserve_cart_for_order(order):
        """Preserve cart contents from order for retry attempts"""
        try:
            # Create cart data from order items
            cart_data = {}

            for item in order.items.all():
                # Create cart key similar to how it's done in cart views
                if item.variant:
                    cart_key = f"{item.product.id}_variant_{item.variant.id}"
                    variant_name = item.variant.name
                    # Use the actual price from the order item (what was paid)
                    price = str(item.price)
                else:
                    cart_key = f"{item.product.id}_base"
                    variant_name = None
                    # Use the actual price from the order item (what was paid)
                    price = str(item.price)

                cart_data[cart_key] = {
                    'product_id': item.product.id,
                    'variant_id': item.variant.id if item.variant else None,
                    'quantity': item.quantity,
                    'price': price,
                    'name': item.product.name,
                    'variant_name': variant_name,
                }

            # Store cart data in order for later retrieval
            order.preserved_cart_data = json.dumps(cart_data)
            order.save()

            return True

        except Exception as e:
            print(f"Failed to preserve cart for order {order.id}: {e}")
            return False

    @staticmethod
    def restore_cart_from_order(request, order):
        """Restore cart contents from preserved order data"""
        try:
            if hasattr(order, 'preserved_cart_data') and order.preserved_cart_data:
                # Parse preserved cart data
                cart_data = json.loads(order.preserved_cart_data)

                # Restore cart to session
                request.session['cart'] = cart_data
                request.session.modified = True

                return True
            else:
                # Fallback: recreate cart from order items
                return CartPreservationService.recreate_cart_from_order_items(request, order)

        except Exception as e:
            print(f"Failed to restore cart from order {order.id}: {e}")
            return False

    @staticmethod
    def recreate_cart_from_order_items(request, order):
        """Recreate cart from order items as fallback"""
        try:
            cart_data = {}

            for item in order.items.all():
                if item.variant:
                    cart_key = f"{item.product.id}_variant_{item.variant.id}"
                    variant_name = item.variant.name
                    # Use the actual price from the order item (what was paid)
                    price = str(item.price)
                else:
                    cart_key = f"{item.product.id}_base"
                    variant_name = None
                    # Use the actual price from the order item (what was paid)
                    price = str(item.price)

                cart_data[cart_key] = {
                    'product_id': item.product.id,
                    'variant_id': item.variant.id if item.variant else None,
                    'quantity': item.quantity,
                    'price': price,
                    'name': item.product.name,
                    'variant_name': variant_name,
                }

            request.session['cart'] = cart_data
            request.session.modified = True

            return True

        except Exception as e:
            print(f"Failed to recreate cart from order {order.id}: {e}")
            return False


class OrderTrackingService:
    """Service for managing order tracking status updates"""
    
    @staticmethod
    def create_initial_tracking_status(order, created_by=None):
        """Create initial tracking status when order is created"""
        return OrderTrackingStatus.objects.create(
            order=order,
            status='order_received',
            message='Your order has been received and is being processed.',
            created_by=created_by
        )
    
    @staticmethod
    def update_order_status(order, status, message='', created_by=None):
        """Add a new tracking status update to an order"""
        return OrderTrackingStatus.objects.create(
            order=order,
            status=status,
            message=message,
            created_by=created_by
        )
    
    @staticmethod
    def get_order_tracking_history(order):
        """Get complete tracking history for an order"""
        return order.tracking_statuses.all()
    
    @staticmethod
    def get_order_progress_percentage(order):
        """Calculate order progress as percentage based on latest status"""
        latest_status = order.get_latest_tracking_status()
        if not latest_status:
            return 0
        
        status_progress = {
            'order_received': 15,
            'payment_confirmed': 30,
            'processing': 50,
            'packaging': 70,
            'shipped': 85,
            'out_for_delivery': 95,
            'delivered': 100,
            'cancelled': 0,
            'refunded': 0,
        }
        
        return status_progress.get(latest_status.status, 0)
