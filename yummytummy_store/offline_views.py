from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth import authenticate, login
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.db import transaction
from django.utils import timezone
from decimal import Decimal
import json

from .models import Product, ProductVariant, Order, OrderItem, OrderTrackingStatus
from .services import OrderTrackingEmailService
from .forms import OfflineOrderForm, OfflineCustomerForm


def is_sales_team_member(user):
    """Check if user is a member of Sales Team group"""
    return user.groups.filter(name='Sales Team').exists() or user.is_superuser


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
    """Create a new offline order"""
    if request.method == 'POST':
        try:
            with transaction.atomic():
                # Parse form data
                customer_type = request.POST.get('customer_type', 'individual')
                
                # Customer information
                first_name = request.POST.get('first_name', '').strip()
                last_name = request.POST.get('last_name', '').strip()
                email = request.POST.get('email', '').strip()
                phone = request.POST.get('phone', '').strip()
                business_name = request.POST.get('business_name', '').strip() if customer_type == 'business' else ''
                
                # Delivery information
                delivery_address = request.POST.get('delivery_address', '').strip()
                delivery_city = request.POST.get('delivery_city', '').strip()
                delivery_county = request.POST.get('delivery_county', '').strip()
                
                # Order items
                order_items_data = json.loads(request.POST.get('order_items', '[]'))
                
                if not order_items_data:
                    messages.error(request, 'Please add at least one product to the order.')
                    return redirect('yummytummy_store:create_offline_order')
                
                # Calculate total
                total_amount = Decimal('0.00')
                order_items = []
                
                for item_data in order_items_data:
                    product_id = item_data.get('product_id')
                    variant_id = item_data.get('variant_id')
                    quantity = int(item_data.get('quantity', 1))
                    
                    product = get_object_or_404(Product, id=product_id)
                    variant = None
                    
                    if variant_id:
                        variant = get_object_or_404(ProductVariant, id=variant_id, product=product)
                        price = variant.price
                    else:
                        price = product.price
                    
                    item_total = price * quantity
                    total_amount += item_total
                    
                    order_items.append({
                        'product': product,
                        'variant': variant,
                        'quantity': quantity,
                        'price': price,
                        'total': item_total
                    })
                
                # Create order
                order = Order.objects.create(
                    first_name=first_name,
                    last_name=last_name,
                    email=email,
                    phone=phone,
                    address=delivery_address,
                    city=delivery_city,
                    county=delivery_county,
                    payment_method='offline',
                    payment_status='pending',
                    total_amount=total_amount,
                    subtotal_amount=total_amount,  # Set subtotal to avoid calculation error
                    created_by=request.user,
                    customer_type=customer_type,
                    business_name=business_name,
                    order_notes=f'Offline order created by {request.user.get_full_name() or request.user.username}'
                )
                
                # Create order items
                for item_data in order_items:
                    OrderItem.objects.create(
                        order=order,
                        product=item_data['product'],
                        variant=item_data['variant'],
                        quantity=item_data['quantity'],
                        price=item_data['price']
                    )
                
                # Create initial tracking status
                tracking_status = OrderTrackingStatus.objects.create(
                    order=order,
                    status='offline_order_created',
                    message=f'Offline order created by {request.user.get_full_name() or request.user.username}',
                    created_by=request.user
                )
                
                # Send email notifications
                try:
                    # Send business notification
                    send_business_notification(order, request.user)
                    
                    # Send customer confirmation
                    OrderTrackingEmailService.send_status_update_email(order, tracking_status)
                    
                except Exception as e:
                    messages.warning(request, f'Order created successfully but email notification failed: {str(e)}')
                
                messages.success(request, f'Offline order {order.get_order_number()} created successfully!')
                return redirect('yummytummy_store:offline_order_success', order_id=order.id)
                
        except Exception as e:
            import traceback
            print(f"Order creation error: {str(e)}")
            print(f"Traceback: {traceback.format_exc()}")
            messages.error(request, f'Error creating order: {str(e)}')
            return redirect('yummytummy_store:create_offline_order')
    
    # GET request - show form
    products = Product.objects.filter(is_available=True).prefetch_related('variants')
    context = {
        'products': products,
        'user': request.user,
    }
    return render(request, 'yummytummy_store/offline/create_order.html', context)


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
                'size': variant.size,
                'price': str(variant.price),
                'stock_quantity': variant.stock_quantity,
            })
        
        return JsonResponse({
            'success': True,
            'variants': variants_data,
            'base_price': str(product.price)
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })


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
        recipient_list=['livegreatagrilife@gmail.com'],
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
