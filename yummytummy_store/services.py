"""
Email and order tracking services for YummyTummy store.
Handles automatic account creation and order tracking emails.
"""

import json
import logging
from urllib.parse import quote
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
from django.core import signing
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils import timezone
from .models import Order, AutoCreatedAccount, OrderTrackingStatus

# Get logger
logger = logging.getLogger(__name__)


def _site_url():
    return getattr(settings, 'SITE_URL', 'https://www.yummytummy.co.ke').rstrip('/')


def _email_context(**extra):
    context = {
        'site_name': 'YummyTummy',
        'site_url': _site_url(),
        'support_email': getattr(settings, 'ADMIN_EMAIL', 'info@yummytummy.co.ke'),
        'admin_email': getattr(settings, 'ADMIN_EMAIL', 'info@yummytummy.co.ke'),
        'orders_email': getattr(settings, 'ORDERS_EMAIL', 'orders@yummytummy.co.ke'),
    }
    context.update(extra)
    return context


class OrderTrackingEmailService:
    """Service for handling order tracking emails and account creation"""
    
    @staticmethod
    def create_user_account(order_data):
        """Create a passwordless account for digital purchases and tracking."""
        email = order_data['email']
        first_name = order_data['first_name']
        last_name = order_data['last_name']
        
        # Check if user already exists
        existing_user = User.objects.filter(email=email).first()
        if existing_user:
            return existing_user, False
        
        # Create new user
        user = User(
            username=email,  # Use email as username
            email=email,
            first_name=first_name,
            last_name=last_name,
        )
        user.set_unusable_password()
        user.save()

        return user, True
    
    @staticmethod
    def create_auto_account_record(user, order):
        """Create the one-time passwordless login record for an order."""
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
            product_name = item.product_name or item.product.name
            variant_name = item.variant_name or (item.variant.name if item.variant else None)
            item_data = {
                'name': product_name,
                'variant_name': variant_name,
                'quantity': item.quantity,
                'price': item.price,
                'total': item.get_cost(),
                'formatted_price': item.get_formatted_price(),
                'formatted_total': item.get_formatted_cost(),
            }
            
            # Create display name with variant
            if variant_name:
                item_data['display_name'] = f"{product_name} - {variant_name}"
            else:
                item_data['display_name'] = product_name
                
            items.append(item_data)
        for item in order.recipe_items.all():
            recipe_title = item.recipe_title or item.recipe.title
            items.append({
                'name': recipe_title,
                'variant_name': None,
                'quantity': item.quantity,
                'price': item.price,
                'total': item.get_cost(),
                'formatted_price': item.get_formatted_price(),
                'formatted_total': item.get_formatted_cost(),
                'display_name': recipe_title,
                'is_digital': True,
            })
        
        return items
    
    @staticmethod
    def get_first_login_url(auto_account, request=None):
        """Generate first-time login URL with token"""
        if request:
            domain = request.get_host()
            protocol = 'https' if request.is_secure() else 'http'
        else:
            # Use SITE_URL from settings (configured for production domain)
            site_url = getattr(settings, 'SITE_URL', 'https://www.yummytummy.co.ke')
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
    def send_magic_login_link(user, request, next_url=''):
        """Send a short-lived, single-use login link without exposing account existence."""
        marker = user.last_login.isoformat() if user.last_login else ''
        token = signing.dumps(
            {
                'user_id': user.pk,
                'email': user.email.lower(),
                'login_marker': marker,
                'next': next_url,
            },
            salt='yummytummy.magic-login',
            compress=True,
        )
        path = reverse('yummytummy_store:magic_link_login', args=[token])
        login_url = request.build_absolute_uri(path)
        context = _email_context(
            user=user,
            login_url=login_url,
            expires_minutes=15,
            customer_name=user.get_full_name() or user.email,
        )
        message = render_to_string(
            'yummytummy_store/emails/magic_login.txt',
            context,
        )
        html_message = render_to_string(
            'yummytummy_store/emails/magic_login.html',
            context,
        )
        try:
            send_mail(
                subject='Your secure YummyTummy sign-in link',
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                html_message=html_message,
                fail_silently=False,
            )
            return True
        except Exception as exc:
            logger.warning('Magic login email failed for user %s: %s', user.pk, exc.__class__.__name__)
            return False
    
    @staticmethod
    def send_regular_order_confirmation(order, request=None):
        """Send regular order confirmation email (for existing users or guest orders)"""
        
        # Format order items
        order_items = OrderTrackingEmailService.format_order_items_for_email(order)
        
        # Prepare email context
        context = _email_context(
            order=order,
            order_items=order_items,
            order_number=order.get_order_number(),
            customer_name=order.get_customer_name(),
        )
        
        # Add login URL if user has account
        if order.user:
            if request:
                domain = request.get_host()
                protocol = 'https' if request.is_secure() else 'http'
            else:
                # Use SITE_URL from settings (configured for production domain)
                site_url = _site_url()
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
            logger.warning('Order confirmation email failed for order %s: %s', order.pk, e.__class__.__name__)
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
            context = _email_context(
                order=order,
                user=order.user,
                login_url=login_url,
                order_items=order_items,
                order_number=order.get_order_number(),
                customer_name=order.get_customer_name(),
                token_expires_days=7,
            )

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
            logger.warning('Payment confirmation email failed for order %s: %s', order.pk, e.__class__.__name__)
            return False

    @staticmethod
    def send_status_update_email(order, tracking_status, request=None):
        """Send email notification when order status is updated"""
        try:
            # Format order items
            order_items = OrderTrackingEmailService.format_order_items_for_email(order)

            # Prepare email context
            context = _email_context(
                order=order,
                tracking_status=tracking_status,
                order_items=order_items,
                order_number=order.get_order_number(),
                customer_name=order.get_customer_name(),
            )

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
            logger.warning('Status update email failed for order %s: %s', order.pk, e.__class__.__name__)
            return False

    @staticmethod
    def send_payment_failed_notification(order, failure_reason=None, request=None):
        """Send email notification when M-Pesa payment fails"""
        try:
            # Format order items
            order_items = OrderTrackingEmailService.format_order_items_for_email(order)

            # Generate retry payment URL (preserve cart for retry)
            retry_token = signing.dumps(
                {'order_id': order.pk, 'email': order.email},
                salt='yummytummy.payment-retry',
                compress=True,
            )
            retry_path = reverse('yummytummy_store:payment_retry', kwargs={'order_id': order.id})
            retry_path = f'{retry_path}?token={quote(retry_token)}'
            if request:
                retry_payment_url = request.build_absolute_uri(retry_path)
                track_order_url = request.build_absolute_uri(reverse('yummytummy_store:guest_order_tracking'))
            else:
                # Fallback URLs for callback context
                site_url = _site_url()
                retry_payment_url = f'{site_url}{retry_path}'
                track_order_url = f"{site_url}{reverse('yummytummy_store:guest_order_tracking')}"

            # Prepare email context
            context = _email_context(
                order=order,
                order_items=order_items,
                order_number=order.get_order_number(),
                customer_name=order.get_customer_name(),
                failure_reason=failure_reason,
                retry_payment_url=retry_payment_url,
                track_order_url=track_order_url,
            )

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
            logger.warning('Payment failure email failed for order %s: %s', order.pk, e.__class__.__name__)
            return False

    @staticmethod
    def send_recipe_purchase_confirmation(order, recipe_purchases):
        """
        Send recipe purchase confirmation email with download links

        Args:
            order: Order instance
            recipe_purchases: QuerySet of RecipePurchase instances
        """
        try:
            # Import here to avoid circular imports
            from django.template.loader import render_to_string
            from django.core.mail import EmailMultiAlternatives
            from django.conf import settings
            from django.utils import timezone
            import pytz

            # Get Kenya timezone for email timestamp
            kenya_tz = pytz.timezone('Africa/Nairobi')
            current_time = timezone.now().astimezone(kenya_tz)

            # Collect related products for upselling (optimized for performance)
            related_products = set()
            try:
                for purchase in recipe_purchases:
                    # Limit database queries by only getting first 3 related products per recipe
                    related_products.update(purchase.recipe.related_products.all()[:3])
                    # Stop if we have enough products
                    if len(related_products) >= 6:
                        break
            except Exception:
                # If related products query fails, continue without them
                related_products = set()

            # Limit to 6 products for email
            related_products = list(related_products)[:6]

            # Email context
            context = _email_context(
                order=order,
                recipe_purchases=recipe_purchases,
                related_products=related_products,
                current_time=current_time,
                request=None,  # Will be set by template context processor if available
            )

            # Render email templates
            subject = f'Your YummyTummy Recipes Are Ready! Order #{order.id}'

            # HTML version
            html_content = render_to_string(
                'yummytummy_store/emails/recipe_purchase_confirmation.html',
                context
            )

            # Plain text version
            text_content = render_to_string(
                'yummytummy_store/emails/recipe_purchase_confirmation.txt',
                context
            )

            # Create email
            email = EmailMultiAlternatives(
                subject=subject,
                body=text_content,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[order.email],
            )

            # Attach HTML version
            email.attach_alternative(html_content, "text/html")

            # Send email
            email.send()

            logger.info('Recipe purchase confirmation email sent for order %s', order.id)
            return True

        except Exception as e:
            logger.warning('Recipe purchase confirmation failed for order %s: %s', order.id, e.__class__.__name__)
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

            for item in order.recipe_items.all():
                cart_data[f'recipe_{item.recipe_id}'] = {
                    'recipe_id': item.recipe_id,
                    'quantity': 1,
                    'price': str(item.price),
                    'name': item.recipe_title or item.recipe.title,
                    'type': 'recipe',
                }

            # Store cart data in order for later retrieval
            order.preserved_cart_data = json.dumps(cart_data)
            order.save()

            return True

        except Exception as e:
            logger.warning('Cart preservation failed for order %s: %s', order.pk, e.__class__.__name__)
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
            logger.warning('Cart restoration failed for order %s: %s', order.pk, e.__class__.__name__)
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

            for item in order.recipe_items.all():
                cart_data[f'recipe_{item.recipe_id}'] = {
                    'recipe_id': item.recipe_id,
                    'quantity': 1,
                    'price': str(item.price),
                    'name': item.recipe_title or item.recipe.title,
                    'type': 'recipe',
                }

            request.session['cart'] = cart_data
            request.session.modified = True

            return True

        except Exception as e:
            logger.warning('Cart recreation failed for order %s: %s', order.pk, e.__class__.__name__)
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
            'order_received': 10,
            'payment_confirmed': 30,
            'payment_failed': 0,
            'processing': 50,
            'packaging': 70,
            'shipped': 85,
            'out_for_delivery': 95,
            'delivered': 100,
            'cancelled': 0,
            'refunded': 0,
        }
        
        return status_progress.get(latest_status.status, 0)
