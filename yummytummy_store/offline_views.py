from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth import authenticate, login
from django.contrib import messages
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.db import transaction
from django.db.models import F
from django.utils import timezone
from decimal import Decimal
import json
import logging

from .models import Product, ProductVariant, Order, OrderItem, OrderTrackingStatus
from .services import OrderTrackingEmailService
from .forms import OfflineOrderForm, OfflineCustomerForm
from .payment_services import PaymentService

logger = logging.getLogger(__name__)


def is_sales_team_member(user):
    """Require the explicit operational permissions assigned to sales staff."""
    return user.is_active and (
        user.is_superuser
        or (
            user.has_perm('yummytummy_store.add_order')
            and user.has_perm('yummytummy_store.view_product')
        )
    )


@login_required
@user_passes_test(is_sales_team_member)
def offline_orders_dashboard(request):
    """Main dashboard for offline order management"""
    context = {
        'user': request.user,
        'is_sales_team': request.user.groups.filter(name='Sales Team').exists(),
        'is_superuser': request.user.is_superuser,
    }
    return render(request, 'yummytummy_store/offline/dashboard.html', context)




@login_required
@user_passes_test(is_sales_team_member)
def create_offline_order(request):
    """Create a validated manual order using current database prices and stock."""
    customer_form = OfflineCustomerForm(request.POST or None)
    order_form = OfflineOrderForm(request.POST or None, initial={'order_items': []})

    if request.method == 'POST' and customer_form.is_valid() and order_form.is_valid():
        customer = customer_form.cleaned_data
        order_data = order_form.cleaned_data
        try:
            with transaction.atomic():
                resolved_items = []
                subtotal = Decimal('0.00')

                for submitted in order_data['order_items']:
                    product = Product.objects.select_for_update().get(
                        pk=submitted['product_id'],
                        is_available=True,
                    )
                    quantity = submitted['quantity']
                    variant = None
                    if submitted['variant_id']:
                        variant = ProductVariant.objects.select_for_update().get(
                            pk=submitted['variant_id'],
                            product=product,
                        )
                        unit_price = variant.calculated_price
                        available = variant.stock_quantity
                    else:
                        unit_price = product.price
                        available = product.stock_quantity

                    if product.track_inventory and available < quantity:
                        label = f'{product.name} - {variant.name}' if variant else product.name
                        raise ValueError(f'Only {available} units of {label} are available.')

                    resolved_items.append((product, variant, quantity, unit_price))
                    subtotal += unit_price * quantity

                order = Order.objects.create(
                    first_name=customer['first_name'],
                    last_name=customer['last_name'],
                    email=customer['email'],
                    phone=customer['phone'],
                    address=customer['delivery_address'],
                    city=customer['delivery_city'],
                    county=customer['delivery_county'],
                    payment_method='offline',
                    payment_status='pending',
                    total_amount=subtotal,
                    subtotal_amount=subtotal,
                    created_by=request.user,
                    customer_type=customer['customer_type'],
                    business_name=customer.get('business_name') or '',
                    order_notes=order_data.get('order_notes', ''),
                )

                for product, variant, quantity, unit_price in resolved_items:
                    OrderItem.objects.create(
                        order=order,
                        product=product,
                        variant=variant,
                        product_name=product.name,
                        variant_name=variant.name if variant else '',
                        quantity=quantity,
                        price=unit_price,
                    )
                    if product.track_inventory:
                        if variant:
                            ProductVariant.objects.filter(pk=variant.pk).update(
                                stock_quantity=F('stock_quantity') - quantity
                            )
                        else:
                            Product.objects.filter(pk=product.pk).update(
                                stock_quantity=F('stock_quantity') - quantity
                            )

                PaymentService.ensure_payment(order, 'offline')
                tracking_status = OrderTrackingStatus.objects.create(
                    order=order,
                    status='offline_order_created',
                    message='Manual order captured by the sales team.',
                    created_by=request.user,
                )

                transaction.on_commit(lambda: _send_offline_notifications(order, request.user, tracking_status))

            messages.success(request, f'Offline order {order.get_order_number()} created successfully.')
            return redirect('yummytummy_store:offline_order_success', order_id=order.pk)
        except (Product.DoesNotExist, ProductVariant.DoesNotExist):
            messages.error(request, 'A selected product or variant is no longer available. Refresh and try again.')
        except ValueError as exc:
            messages.error(request, str(exc))
        except Exception as exc:
            logger.exception('Offline order creation failed with %s', exc.__class__.__name__)
            messages.error(request, 'The order could not be created. No changes were saved.')
    elif request.method == 'POST':
        messages.error(request, 'Review the highlighted customer and order details.')

    products = Product.objects.filter(is_available=True).prefetch_related('variants')
    return render(request, 'yummytummy_store/offline/create_order.html', {
        'products': products,
        'user': request.user,
        'customer_form': customer_form,
        'order_form': order_form,
    })


def _send_offline_notifications(order, sales_person, tracking_status):
    try:
        send_business_notification(order, sales_person)
    except Exception as exc:
        logger.warning('Business notification failed for order %s: %s', order.pk, exc.__class__.__name__)

    try:
        from .notifications import NotificationService
        NotificationService.enqueue_tracking_update(tracking_status)
    except Exception as exc:
        logger.warning('Customer notification queue failed for order %s: %s', order.pk, exc.__class__.__name__)


@login_required
@user_passes_test(is_sales_team_member)
def offline_order_success(request, order_id):
    """Show success page after creating offline order"""
    order = get_object_or_404(Order, id=order_id, created_by=request.user)
    context = {
        'order': order,
        'user': request.user,
    }
    return render(request, 'yummytummy_store/offline/order_success.html', context)


@require_http_methods(["GET"])
@login_required
@user_passes_test(is_sales_team_member)
def get_product_variants(request, product_id):
    """API endpoint to get product variants"""
    try:
        product = get_object_or_404(Product, id=product_id)
        variants = product.variants.all()
        
        variants_data = []
        for variant in variants:
            variants_data.append({
                'id': variant.id,
                'name': variant.name,
                'size': variant.name,
                'price': str(variant.calculated_price),
                'stock_quantity': variant.stock_quantity,
            })
        
        return JsonResponse({
            'success': True,
            'variants': variants_data,
            'base_price': str(product.price)
        })
    except Exception as exc:
        logger.warning('Variant lookup failed for product %s: %s', product_id, exc.__class__.__name__)
        return JsonResponse({
            'success': False,
            'error': 'Variants are temporarily unavailable.'
        }, status=400)


def send_business_notification(order, sales_person):
    """Send email notification to business about new offline order"""
    from django.core.mail import send_mail
    from django.template.loader import render_to_string
    from django.conf import settings
    
    # Prepare email context
    context = {
        'order': order,
        'sales_person': sales_person,
        'order_items': order.items.all(),
        'current_time': timezone.now(),
        'site_name': 'YummyTummy',
        'support_email': getattr(settings, 'ADMIN_EMAIL', 'info@yummytummy.co.ke'),
        'admin_email': getattr(settings, 'ADMIN_EMAIL', 'info@yummytummy.co.ke'),
        'orders_email': getattr(settings, 'ORDERS_EMAIL', 'orders@yummytummy.co.ke'),
    }
    
    # Render email content
    subject = f'New Offline Order Created - Order #{order.get_order_number()}'
    html_message = render_to_string('yummytummy_store/emails/business_offline_order_notification.html', context)
    plain_message = render_to_string('yummytummy_store/emails/business_offline_order_notification.txt', context)
    
    # Send email
    send_mail(
        subject=subject,
        message=plain_message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[getattr(settings, 'ORDERS_EMAIL', settings.BUSINESS_NOTIFICATION_EMAIL)],
        html_message=html_message,
        fail_silently=False,
    )


# Sales Team Authentication Views
def sales_login(request):
    """Login page specifically for sales team"""
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        user = authenticate(request, username=username, password=password)
        if user is not None and is_sales_team_member(user):
            login(request, user)
            return redirect('yummytummy_store:offline_orders_dashboard')
        else:
            messages.error(request, 'Invalid credentials or insufficient permissions.')
    
    return render(request, 'yummytummy_store/offline/login.html')


@login_required
@user_passes_test(is_sales_team_member)
def offline_orders_list(request):
    """List all offline orders created by the current user"""
    if request.user.is_superuser:
        orders = Order.objects.filter(created_by__isnull=False).order_by('-created')
    else:
        orders = Order.objects.filter(created_by=request.user).order_by('-created')
    
    context = {
        'orders': orders,
        'user': request.user,
    }
    return render(request, 'yummytummy_store/offline/orders_list.html', context)
