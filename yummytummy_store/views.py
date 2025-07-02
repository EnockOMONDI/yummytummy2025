from django.shortcuts import render, get_object_or_404, redirect
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.contrib.auth import login, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Q, Sum, Count, Avg
from django.db.models.functions import TruncDate
from django.urls import reverse
from django.utils.crypto import get_random_string
from django.utils import timezone
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from datetime import datetime, timedelta
from .models import Category, Product, ProductVariant, Ingredient, Order, OrderItem, Coupon, CouponUsage, AutoCreatedAccount, OrderTrackingStatus
from .forms import CartAddProductForm, ProductSearchForm, ContactForm, CheckoutForm, PaymentForm, CouponApplyForm
from .mpesa_service import MPesaService
from .services import OrderTrackingEmailService, OrderTrackingService

def home(request):
    """View for the homepage"""
    # Get regular featured products for the product slider
    featured_products = Product.objects.filter(is_available=True)[:4]

    # Get the highlighted featured product for the hero section
    # First try to get a seasonal or limited_time featured product
    highlighted_product = Product.objects.filter(
        is_available=True,
        is_featured=True
    ).order_by('-updated').first()

    # If no featured product is found, use the first available product
    if not highlighted_product and featured_products:
        highlighted_product = featured_products[0]

    # Get cart form for the highlighted product
    cart_product_form = None
    if highlighted_product:
        cart_product_form = CartAddProductForm()

    categories = Category.objects.all()

    context = {
        'featured_products': featured_products,
        'highlighted_product': highlighted_product,
        'cart_product_form': cart_product_form,
        'categories': categories,
    }
    return render(request, 'yummytummy_store/home.html', context)

def product_list(request, category_slug=None):
    """View for listing products, optionally filtered by category"""
    category = None
    categories = Category.objects.all()
    products = Product.objects.filter(is_available=True)

    if category_slug:
        category = get_object_or_404(Category, slug=category_slug)
        products = products.filter(category=category)

    # Search functionality
    form = ProductSearchForm(request.GET)
    if form.is_valid() and form.cleaned_data['query']:
        query = form.cleaned_data['query']
        products = products.filter(
            Q(name__icontains=query) |
            Q(description__icontains=query)
        )

    context = {
        'category': category,
        'categories': categories,
        'products': products,
        'form': form,
    }
    return render(request, 'yummytummy_store/product/list.html', context)

def product_detail(request, slug):
    """View for product details"""
    product = get_object_or_404(Product, slug=slug, is_available=True)
    cart_product_form = CartAddProductForm()

    context = {
        'product': product,
        'cart_product_form': cart_product_form,
    }
    return render(request, 'yummytummy_store/product/detail.html', context)

def about(request):
    """View for the about page"""
    return render(request, 'yummytummy_store/about.html')

def contact(request):
    """View for the contact page with form handling"""
    if request.method == 'POST':
        form = ContactForm(request.POST)
        if form.is_valid():
            # In a real application, you would process the form data here
            # (e.g., send an email, save to database, etc.)
            messages.success(request, 'Your message has been sent. We will contact you soon!')
            return redirect('yummytummy_store:contact')
    else:
        form = ContactForm()

    return render(request, 'yummytummy_store/contact.html', {'form': form})

# Shopping Cart Views
@require_POST
def cart_add(request, product_id):
    """Add a product to the cart"""
    product = get_object_or_404(Product, id=product_id)
    form = CartAddProductForm(request.POST)

    if form.is_valid():
        cd = form.cleaned_data

        # Initialize the cart in the session if it doesn't exist
        if 'cart' not in request.session:
            request.session['cart'] = {}

        # Get the cart from the session
        cart = request.session['cart']

        # Handle variant selection
        selected_variant = cd.get('selected_variant')
        variant = None
        variant_price = product.price
        variant_name = product.name

        if selected_variant and selected_variant != 'base':
            try:
                variant = ProductVariant.objects.get(id=selected_variant, product=product)
                variant_price = product.price + variant.additional_price
                variant_name = f"{product.name} - {variant.name}"
            except ProductVariant.DoesNotExist:
                # Fall back to base product if variant not found
                pass

        # Create a unique cart key that includes variant information
        if variant:
            cart_key = f"{product_id}_variant_{variant.id}"
        else:
            cart_key = f"{product_id}_base"

        # Update or add the product/variant to the cart
        if cart_key in cart:
            if cd['update']:
                cart[cart_key]['quantity'] = cd['quantity']
            else:
                cart[cart_key]['quantity'] += cd['quantity']
        else:
            cart[cart_key] = {
                'product_id': product_id,
                'variant_id': variant.id if variant else None,
                'quantity': cd['quantity'],
                'price': str(variant_price),
                'name': variant_name,
                'variant_name': variant.name if variant else None,
            }

        # Mark the session as modified to ensure it gets saved
        request.session.modified = True
        messages.success(request, f'{variant_name} added to your cart.')
    else:
        # Add error messages for form validation failures
        for field, errors in form.errors.items():
            for error in errors:
                messages.error(request, f'Error in {field}: {error}')

    return redirect('yummytummy_store:cart_detail')

def cart_remove(request, product_id):
    """Remove a product from the cart"""
    if 'cart' in request.session:
        cart = request.session['cart']

        # Find and remove all cart items for this product (base and variants)
        items_to_remove = []
        product_name = 'Item'

        for cart_key, item_data in cart.items():
            if item_data.get('product_id') == int(product_id):
                items_to_remove.append(cart_key)
                product_name = item_data.get('name', 'Item')

        # Remove all found items
        for cart_key in items_to_remove:
            del cart[cart_key]

        if items_to_remove:
            # Mark the session as modified
            request.session.modified = True
            messages.info(request, f'{product_name} removed from your cart.')

    return redirect('yummytummy_store:cart_detail')

@require_POST
def cart_update(request, cart_key):
    """Update quantity of a specific cart item using cart key"""
    form = CartAddProductForm(request.POST)

    if form.is_valid():
        cd = form.cleaned_data

        if 'cart' in request.session:
            cart = request.session['cart']

            if cart_key in cart:
                # Update the quantity for this specific cart item
                cart[cart_key]['quantity'] = cd['quantity']

                # Mark the session as modified
                request.session.modified = True

                item_name = cart[cart_key].get('name', 'Item')
                messages.success(request, f'{item_name} quantity updated to {cd["quantity"]}.')
            else:
                messages.error(request, 'Item not found in cart.')
        else:
            messages.error(request, 'Cart is empty.')
    else:
        # Add error messages for form validation failures
        for field, errors in form.errors.items():
            for error in errors:
                messages.error(request, f'Error in {field}: {error}')

    return redirect('yummytummy_store:cart_detail')

def cart_remove_item(request, cart_key):
    """Remove a specific cart item using cart key"""
    if 'cart' in request.session:
        cart = request.session['cart']

        if cart_key in cart:
            # Get the item name before removing it
            item_name = cart[cart_key].get('name', 'Item')

            # Remove the specific cart item
            del cart[cart_key]

            # Mark the session as modified
            request.session.modified = True
            messages.info(request, f'{item_name} removed from your cart.')
        else:
            messages.error(request, 'Item not found in cart.')
    else:
        messages.error(request, 'Cart is empty.')

    return redirect('yummytummy_store:cart_detail')

def cart_detail(request):
    """View the cart contents"""
    # Ensure the cart exists in the session
    if 'cart' not in request.session:
        request.session['cart'] = {}

    cart = request.session['cart']
    cart_items = []
    subtotal = 0

    # Process cart items
    for cart_key, item_data in cart.items():
        try:
            # Convert price to float safely
            price = float(item_data['price'])
            quantity = int(item_data['quantity'])
            item_subtotal = price * quantity
            subtotal += item_subtotal

            # Get the actual product for additional information
            product_id = item_data.get('product_id')
            product = None
            if product_id:
                try:
                    product = Product.objects.get(id=product_id)
                except Product.DoesNotExist:
                    continue

            cart_items.append({
                'cart_key': cart_key,
                'id': product_id,
                'product': product,
                'name': item_data['name'],
                'variant_name': item_data.get('variant_name'),
                'price': price,
                'quantity': quantity,
                'subtotal': item_subtotal,
            })
        except (ValueError, KeyError) as e:
            # Handle any corrupted cart data
            messages.error(request, f"Error processing cart item: {e}")
            continue

    # Get coupon from session if exists
    coupon_id = request.session.get('coupon_id')
    coupon = None
    discount = 0

    if coupon_id:
        try:
            coupon = Coupon.objects.get(id=coupon_id, is_active=True)

            # Validate coupon
            now = timezone.now()
            if now >= coupon.valid_from and now <= coupon.valid_to and subtotal >= coupon.min_order_amount:
                # Calculate discount
                discount = coupon.calculate_discount(subtotal)
            else:
                # Coupon no longer valid, remove from session
                del request.session['coupon_id']
                coupon = None
                messages.warning(request, "The applied coupon is no longer valid.")
        except Coupon.DoesNotExist:
            # Coupon no longer exists, remove from session
            del request.session['coupon_id']
            messages.warning(request, "The applied coupon is no longer valid.")

    # Calculate total after discount
    total = subtotal - discount

    # Initialize coupon form
    coupon_form = CouponApplyForm()

    # Ensure the session is saved
    request.session.modified = True

    context = {
        'cart_items': cart_items,
        'subtotal': subtotal,
        'discount': discount,
        'total': total,
        'coupon': coupon,
        'coupon_form': coupon_form,
    }
    return render(request, 'yummytummy_store/cart/detail.html', context)


@require_POST
def coupon_apply(request):
    """Apply a coupon to the cart"""
    now = timezone.now()
    form = CouponApplyForm(request.POST)

    # Get cart total for validation
    cart = request.session.get('cart', {})
    cart_total = 0
    for item_data in cart.values():
        try:
            price = float(item_data['price'])
            quantity = int(item_data['quantity'])
            cart_total += price * quantity
        except (ValueError, KeyError):
            continue

    if form.is_valid():
        code = form.cleaned_data['code']

        try:
            coupon = Coupon.objects.get(
                code=code,
                is_active=True,
                valid_from__lte=now,
                valid_to__gte=now
            )

            # Check minimum order amount
            if cart_total < coupon.min_order_amount:
                messages.error(
                    request,
                    f"This coupon requires a minimum order of KSh {coupon.min_order_amount:,.2f}."
                )
                return redirect('yummytummy_store:cart_detail')

            # Check usage limit
            if coupon.usage_count >= coupon.usage_limit:
                messages.error(request, "This coupon has reached its usage limit.")
                return redirect('yummytummy_store:cart_detail')

            # Check per-customer limit if user is authenticated
            if request.user.is_authenticated:
                user_usage_count = CouponUsage.objects.filter(
                    coupon=coupon,
                    user=request.user
                ).count()

                if user_usage_count >= coupon.per_customer_limit:
                    messages.error(
                        request,
                        f"You have already used this coupon {user_usage_count} times, which is the maximum allowed."
                    )
                    return redirect('yummytummy_store:cart_detail')

            # Store coupon ID in session
            request.session['coupon_id'] = coupon.id

            # Calculate discount for display
            discount = coupon.calculate_discount(cart_total)

            if coupon.discount_type == 'percentage':
                messages.success(
                    request,
                    f"Coupon '{code}' applied successfully! {coupon.discount_value:.0f}% discount (KSh {discount:,.2f}) has been applied to your cart."
                )
            else:
                messages.success(
                    request,
                    f"Coupon '{code}' applied successfully! KSh {discount:,.2f} discount has been applied to your cart."
                )

        except Coupon.DoesNotExist:
            messages.error(request, "Invalid coupon code or the coupon has expired.")
            if 'coupon_id' in request.session:
                del request.session['coupon_id']
    else:
        for error in form.errors.get('code', []):
            messages.error(request, error)

    return redirect('yummytummy_store:cart_detail')


@require_POST
def coupon_remove(request):
    """Remove the applied coupon from the cart"""
    if 'coupon_id' in request.session:
        del request.session['coupon_id']
        messages.success(request, "Coupon has been removed from your cart.")

    return redirect('yummytummy_store:cart_detail')


def checkout(request):
    """Checkout page with shipping address form"""
    # Check if cart is empty
    if 'cart' not in request.session or not request.session['cart']:
        messages.warning(request, "Your cart is empty. Please add some products before proceeding to checkout.")
        return redirect('yummytummy_store:product_list')

    # Process cart items
    cart = request.session['cart']
    cart_items = []
    subtotal = 0

    for cart_key, item_data in cart.items():
        try:
            price = float(item_data['price'])
            quantity = int(item_data['quantity'])
            item_subtotal = price * quantity
            subtotal += item_subtotal

            cart_items.append({
                'cart_key': cart_key,
                'id': item_data.get('product_id'),
                'name': item_data['name'],
                'variant_name': item_data.get('variant_name'),
                'price': price,
                'quantity': quantity,
                'subtotal': item_subtotal,
            })
        except (ValueError, KeyError) as e:
            messages.error(request, f"Error processing cart item: {e}")
            continue

    # Get coupon from session if exists
    coupon_id = request.session.get('coupon_id')
    coupon = None
    discount = 0

    if coupon_id:
        try:
            coupon = Coupon.objects.get(id=coupon_id, is_active=True)

            # Validate coupon
            now = timezone.now()
            if now >= coupon.valid_from and now <= coupon.valid_to and subtotal >= coupon.min_order_amount:
                # Calculate discount
                discount = coupon.calculate_discount(subtotal)
            else:
                # Coupon no longer valid, remove from session
                del request.session['coupon_id']
                coupon = None
                messages.warning(request, "The applied coupon is no longer valid.")
        except Coupon.DoesNotExist:
            # Coupon no longer exists, remove from session
            del request.session['coupon_id']
            messages.warning(request, "The applied coupon is no longer valid.")

    # Calculate total after discount
    total = subtotal - discount

    if request.method == 'POST':
        form = CheckoutForm(request.POST)
        if form.is_valid():
            # Store checkout data in session for payment step
            checkout_data = form.cleaned_data
            request.session['checkout_data'] = {
                'first_name': checkout_data['first_name'],
                'last_name': checkout_data['last_name'],
                'email': checkout_data['email'],
                'phone': checkout_data['phone'],
                'address': checkout_data['address'],
                'area': checkout_data['area'],
                'estate': checkout_data['estate'],
                'building': checkout_data['building'],
                'landmark': checkout_data['landmark'],
                'order_notes': checkout_data['order_notes'],
                'subtotal_amount': float(subtotal),
                'discount_amount': float(discount),
                'total_amount': float(total),
                'coupon_id': coupon_id,
            }
            request.session.modified = True
            return redirect('yummytummy_store:payment')
    else:
        form = CheckoutForm()

    context = {
        'form': form,
        'cart_items': cart_items,
        'subtotal': subtotal,
        'discount': discount,
        'total': total,
        'coupon': coupon,
    }
    return render(request, 'yummytummy_store/checkout/shipping.html', context)


def payment(request):
    """Payment page with payment method selection"""
    # Check if checkout data exists in session
    if 'checkout_data' not in request.session:
        messages.warning(request, "Please complete the shipping information first.")
        return redirect('yummytummy_store:checkout')

    # Check if cart is empty
    if 'cart' not in request.session or not request.session['cart']:
        messages.warning(request, "Your cart is empty. Please add some products before proceeding to checkout.")
        return redirect('yummytummy_store:product_list')

    checkout_data = request.session['checkout_data']
    subtotal_amount = checkout_data.get('subtotal_amount', 0)
    discount_amount = checkout_data.get('discount_amount', 0)
    total_amount = checkout_data['total_amount']
    coupon_id = checkout_data.get('coupon_id')

    if request.method == 'POST':
        form = PaymentForm(request.POST)
        if form.is_valid():
            payment_method = form.cleaned_data['payment_method']

            # Automatic Account Creation Logic
            user_account = None
            auto_account = None
            temp_password = None

            # Check if user already exists
            existing_user = User.objects.filter(email=checkout_data['email']).first()

            if existing_user:
                # Link order to existing user
                user_account = existing_user
            else:
                # Create new user account automatically
                user_account, temp_password = OrderTrackingEmailService.create_user_account(checkout_data)

                # Create AutoCreatedAccount record for tracking (will be linked after order creation)
                auto_account_data = {
                    'user': user_account,
                    'temp_password': temp_password
                }

            # Create the order
            order = Order(
                user=user_account,  # Link order to user account
                first_name=checkout_data['first_name'],
                last_name=checkout_data['last_name'],
                email=checkout_data['email'],
                phone=checkout_data['phone'],
                address=checkout_data['address'],
                area=checkout_data.get('area', ''),
                estate=checkout_data.get('estate', ''),
                building=checkout_data.get('building', ''),
                landmark=checkout_data.get('landmark', ''),
                order_notes=checkout_data['order_notes'],
                payment_method=payment_method,
                payment_status='pending',
                subtotal_amount=subtotal_amount,
                discount_amount=discount_amount,
                total_amount=total_amount,
                auto_created_account=bool(temp_password),  # Mark if account was auto-created
            )

            # Add M-Pesa phone number if applicable
            if payment_method == 'mpesa':
                order.mpesa_phone = form.cleaned_data['mpesa_phone']

            # Add coupon if applicable
            if coupon_id:
                try:
                    coupon = Coupon.objects.get(id=coupon_id, is_active=True)
                    order.coupon = coupon
                except Coupon.DoesNotExist:
                    pass

            # Save the order
            order.save()

            # Create order items
            cart = request.session['cart']
            for cart_key, item_data in cart.items():
                try:
                    product_id = item_data.get('product_id')
                    product = Product.objects.get(id=product_id)
                    price = float(item_data['price'])
                    quantity = int(item_data['quantity'])
                    variant_id = item_data.get('variant_id')

                    # Get variant if specified
                    variant = None
                    if variant_id:
                        try:
                            variant = ProductVariant.objects.get(id=variant_id)
                        except ProductVariant.DoesNotExist:
                            pass

                    OrderItem.objects.create(
                        order=order,
                        product=product,
                        variant=variant,
                        price=price,
                        quantity=quantity
                    )
                except (Product.DoesNotExist, ValueError, KeyError) as e:
                    messages.error(request, f"Error processing order item: {e}")
                    continue

            # Record coupon usage if applicable
            if coupon_id and order.coupon:
                # Increment coupon usage count
                coupon = order.coupon
                coupon.usage_count += 1
                coupon.save()

                # Create coupon usage record
                CouponUsage.objects.create(
                    coupon=coupon,
                    order=order,
                    user=user_account,
                    discount_amount=discount_amount
                )

            # Create AutoCreatedAccount record if account was auto-created
            if temp_password:
                auto_account = OrderTrackingEmailService.create_auto_account_record(
                    user_account, order, temp_password
                )

            # Process M-Pesa payment if applicable
            if payment_method == 'mpesa':
                try:
                    # Generate callback URL for M-Pesa
                    if settings.DEBUG:
                        # For development, use a placeholder URL since localhost won't work with M-Pesa
                        callback_url = 'https://webhook.site/unique-id'
                    else:
                        # For production, use the actual callback URL
                        callback_url = request.build_absolute_uri(reverse('yummytummy_store:mpesa_callback'))

                    # Initialize M-Pesa service
                    mpesa_service = MPesaService()

                    # Initiate STK Push
                    mpesa_response = mpesa_service.initiate_stk_push(
                        phone_number=order.mpesa_phone,
                        amount=float(order.total_amount),
                        order_id=order.id,
                        callback_url=callback_url
                    )

                    if mpesa_response['success']:
                        # Update order with M-Pesa details
                        order.mpesa_checkout_request_id = mpesa_response.get('checkout_request_id')
                        order.mpesa_merchant_request_id = mpesa_response.get('merchant_request_id')
                        order.payment_status = 'processing'
                        order.save()

                        messages.success(request,
                            "M-Pesa payment initiated! Please check your phone for the payment prompt.")
                    else:
                        # M-Pesa initiation failed
                        order.payment_status = 'failed'
                        order.save()

                        # Create failed payment tracking status
                        OrderTrackingStatus.objects.create(
                            order=order,
                            status='cancelled',
                            message=f'M-Pesa payment initiation failed: {mpesa_response.get("error", "Unknown error")}'
                        )

                        # Send failed payment notification email
                        try:
                            OrderTrackingEmailService.send_payment_failed_notification(
                                order=order,
                                failure_reason=f"Payment initiation failed: {mpesa_response.get('error', 'Unknown error')}",
                                request=request
                            )
                        except Exception as e:
                            print(f"Failed to send payment failure notification for order {order.id}: {str(e)}")

                        messages.error(request,
                            f"M-Pesa payment failed: {mpesa_response.get('error', 'Unknown error')}")

                except Exception as e:
                    # Handle M-Pesa errors gracefully
                    order.payment_status = 'failed'
                    order.save()

                    # Create failed payment tracking status
                    OrderTrackingStatus.objects.create(
                        order=order,
                        status='cancelled',
                        message=f'M-Pesa payment error: {str(e)}'
                    )

                    # Send failed payment notification email
                    try:
                        OrderTrackingEmailService.send_payment_failed_notification(
                            order=order,
                            failure_reason=f"Payment processing error: {str(e)}",
                            request=request
                        )
                    except Exception as email_error:
                        print(f"Failed to send payment failure notification for order {order.id}: {str(email_error)}")

                    messages.error(request,
                        "There was an error processing your M-Pesa payment. Please try again or contact support.")

            # Create initial order tracking status
            OrderTrackingService.create_initial_tracking_status(order)

            # Store email data in session for later sending (after payment confirmation)
            if temp_password and auto_account:
                request.session['pending_account_email'] = {
                    'order_id': order.id,
                    'user_id': user_account.id,
                    'temp_password': temp_password,
                    'auto_account_id': auto_account.id if auto_account else None
                }
            else:
                request.session['pending_order_email'] = {
                    'order_id': order.id
                }
            request.session.modified = True

            # Store order ID in session for confirmation page
            request.session['order_id'] = order.id

            # Preserve cart data for potential payment retry before clearing
            from .services import CartPreservationService
            CartPreservationService.preserve_cart_for_order(order)

            # Clear cart, checkout data, and coupon
            request.session['cart'] = {}
            if 'checkout_data' in request.session:
                del request.session['checkout_data']
            if 'coupon_id' in request.session:
                del request.session['coupon_id']

            request.session.modified = True

            # Redirect to confirmation page
            return redirect('yummytummy_store:order_confirmation')
    else:
        form = PaymentForm()

    context = {
        'form': form,
        'checkout_data': checkout_data,
        'subtotal_amount': subtotal_amount,
        'discount_amount': discount_amount,
        'total_amount': total_amount,
    }
    return render(request, 'yummytummy_store/checkout/payment.html', context)


def order_confirmation(request):
    """Order confirmation page"""
    # Check if order ID exists in session
    if 'order_id' not in request.session:
        messages.warning(request, "No order information found.")
        return redirect('yummytummy_store:product_list')

    try:
        order = Order.objects.get(id=request.session['order_id'])
        order_items = order.items.all()
    except Order.DoesNotExist:
        messages.error(request, "Order not found.")
        return redirect('yummytummy_store:product_list')

    # Clear order ID from session after displaying confirmation
    del request.session['order_id']
    request.session.modified = True

    context = {
        'order': order,
        'order_items': order_items,
    }
    return render(request, 'yummytummy_store/checkout/confirmation.html', context)


# Order Tracking and Authentication Views

def first_time_login(request, token):
    """Handle first-time login with token from email"""
    try:
        auto_account = AutoCreatedAccount.objects.get(
            first_login_token=token,
            first_login_completed=False
        )

        # Check if token is still valid
        if not auto_account.is_token_valid():
            messages.error(request, "This login link has expired. Please contact support for assistance.")
            return redirect('yummytummy_store:home')

        # Log the user in
        login(request, auto_account.user)

        # Mark first login as completed
        auto_account.mark_first_login_completed()

        messages.success(request, f"Welcome to YummyTummy, {auto_account.user.first_name}! Your account has been activated.")
        messages.info(request, "For security, please consider changing your password in your account settings.")

        # Redirect to order tracking dashboard
        return redirect('yummytummy_store:order_tracking_dashboard')

    except AutoCreatedAccount.DoesNotExist:
        messages.error(request, "Invalid or expired login link. Please contact support for assistance.")
        return redirect('yummytummy_store:home')


@login_required
def order_tracking_dashboard(request):
    """User dashboard for viewing order history and tracking"""
    # Get user's orders
    orders = Order.objects.filter(user=request.user).order_by('-created')

    # Get order tracking information
    orders_with_tracking = []
    for order in orders:
        latest_status = order.get_latest_tracking_status()
        progress_percentage = OrderTrackingService.get_order_progress_percentage(order)

        orders_with_tracking.append({
            'order': order,
            'latest_status': latest_status,
            'progress_percentage': progress_percentage,
            'tracking_history': order.tracking_statuses.all()[:3],  # Show last 3 updates
        })

    context = {
        'orders_with_tracking': orders_with_tracking,
        'user': request.user,
    }
    return render(request, 'yummytummy_store/account/dashboard.html', context)


@login_required
def order_detail_tracking(request, order_id):
    """Detailed view of a specific order with full tracking history"""
    order = get_object_or_404(Order, id=order_id, user=request.user)

    # Get complete tracking history
    tracking_history = OrderTrackingService.get_order_tracking_history(order)
    progress_percentage = OrderTrackingService.get_order_progress_percentage(order)

    # Get order items with variant information
    order_items = []
    for item in order.items.all():
        item_data = {
            'product': item.product,
            'variant': item.variant,
            'quantity': item.quantity,
            'price': item.price,
            'total': item.get_cost(),
            'display_name': f"{item.product.name} - {item.variant.name}" if item.variant else item.product.name,
        }
        order_items.append(item_data)

    context = {
        'order': order,
        'order_items': order_items,
        'tracking_history': tracking_history,
        'progress_percentage': progress_percentage,
        'latest_status': order.get_latest_tracking_status(),
    }
    return render(request, 'yummytummy_store/account/order_detail.html', context)


@login_required
def account_profile(request):
    """User account profile page"""
    # Get user's recent orders
    recent_orders = Order.objects.filter(user=request.user).order_by('-created')[:5]

    # Get account creation info if available
    auto_account = None
    try:
        auto_account = AutoCreatedAccount.objects.get(user=request.user)
    except AutoCreatedAccount.DoesNotExist:
        pass

    context = {
        'user': request.user,
        'recent_orders': recent_orders,
        'auto_account': auto_account,
    }
    return render(request, 'yummytummy_store/account/profile.html', context)


def guest_order_tracking(request):
    """Guest order tracking - allows tracking orders without login"""
    order = None
    error_message = None

    if request.method == 'POST':
        order_number = request.POST.get('order_number', '').strip()
        email = request.POST.get('email', '').strip()

        if order_number and email:
            try:
                # Extract order ID from order number (format: MSL-000123)
                if order_number.startswith('MSL-'):
                    order_id = int(order_number.split('-')[1])
                    order = Order.objects.get(id=order_id, email__iexact=email)

                    # Get tracking information
                    tracking_history = OrderTrackingService.get_order_tracking_history(order)
                    progress_percentage = OrderTrackingService.get_order_progress_percentage(order)

                    # Get order items
                    order_items = []
                    for item in order.items.all():
                        item_data = {
                            'product': item.product,
                            'variant': item.variant,
                            'quantity': item.quantity,
                            'price': item.price,
                            'total': item.get_cost(),
                            'display_name': f"{item.product.name} - {item.variant.name}" if item.variant else item.product.name,
                        }
                        order_items.append(item_data)

                    context = {
                        'order': order,
                        'order_items': order_items,
                        'tracking_history': tracking_history,
                        'progress_percentage': progress_percentage,
                        'is_guest_tracking': True,
                    }
                    return render(request, 'yummytummy_store/account/guest_order_tracking.html', context)
                else:
                    error_message = "Invalid order number format. Order numbers start with 'MSL-'"
            except (ValueError, Order.DoesNotExist):
                error_message = "Order not found. Please check your order number and email address."
        else:
            error_message = "Please enter both order number and email address."

    context = {
        'error_message': error_message,
    }
    return render(request, 'yummytummy_store/account/guest_order_tracking.html', context)


def payment_retry(request, order_id):
    """Allow customers to retry payment for failed orders"""
    try:
        order = get_object_or_404(Order, id=order_id, payment_status='failed')

        # Restore cart contents from order
        from .services import CartPreservationService
        cart_restored = CartPreservationService.restore_cart_from_order(request, order)

        if cart_restored:
            # Restore checkout data from order
            request.session['checkout_data'] = {
                'first_name': order.first_name,
                'last_name': order.last_name,
                'email': order.email,
                'phone': order.phone,
                'address': order.address,
                'area': order.area,
                'estate': order.estate,
                'building': order.building,
                'landmark': order.landmark,
                'order_notes': order.order_notes,
                'subtotal_amount': float(order.subtotal_amount),
                'discount_amount': float(order.discount_amount),
                'total_amount': float(order.total_amount),
                'coupon_id': order.coupon.id if order.coupon else None,
            }
            request.session.modified = True

            messages.success(request,
                f"Your cart has been restored for order {order.get_order_number()}. Please try your payment again.")

            # Redirect to payment page
            return redirect('yummytummy_store:payment')
        else:
            messages.error(request,
                "Unable to restore your cart. Please add items to your cart and try again.")
            return redirect('yummytummy_store:product_list')

    except Order.DoesNotExist:
        messages.error(request, "Order not found or payment retry not available.")
        return redirect('yummytummy_store:guest_order_tracking')
    except Exception as e:
        messages.error(request, "An error occurred while preparing your payment retry. Please contact support.")
        return redirect('yummytummy_store:guest_order_tracking')


# M-Pesa Integration Views

@csrf_exempt
def mpesa_callback(request):
    """
    Handle M-Pesa payment callback from Safaricom
    """
    if request.method == 'POST':
        try:
            import json
            import logging

            logger = logging.getLogger(__name__)

            # Parse the callback data
            callback_data = json.loads(request.body.decode('utf-8'))
            logger.info(f"M-Pesa callback received: {callback_data}")

            # Extract callback information
            stk_callback = callback_data.get('Body', {}).get('stkCallback', {})
            merchant_request_id = stk_callback.get('MerchantRequestID')
            checkout_request_id = stk_callback.get('CheckoutRequestID')
            result_code = stk_callback.get('ResultCode')
            result_desc = stk_callback.get('ResultDesc')

            # Find the order using checkout request ID
            try:
                order = Order.objects.get(mpesa_checkout_request_id=checkout_request_id)

                if result_code == 0:
                    # Payment successful
                    callback_metadata = stk_callback.get('CallbackMetadata', {}).get('Item', [])

                    # Extract payment details
                    amount = None
                    receipt_number = None
                    transaction_date = None
                    phone_number = None

                    for item in callback_metadata:
                        name = item.get('Name')
                        value = item.get('Value')

                        if name == 'Amount':
                            amount = value
                        elif name == 'MpesaReceiptNumber':
                            receipt_number = value
                        elif name == 'TransactionDate':
                            transaction_date = value
                        elif name == 'PhoneNumber':
                            phone_number = value

                    # Update order with payment details
                    order.payment_status = 'completed'
                    order.transaction_id = receipt_number
                    order.mpesa_receipt_number = receipt_number

                    if transaction_date:
                        from datetime import datetime
                        from django.utils import timezone as django_timezone
                        import pytz
                        try:
                            # Parse M-Pesa date format (YYYYMMDDHHMMSS)
                            # M-Pesa timestamps are in Kenya time (EAT)
                            naive_datetime = datetime.strptime(str(transaction_date), '%Y%m%d%H%M%S')

                            # Make timezone-aware in Kenya timezone
                            kenya_tz = pytz.timezone('Africa/Nairobi')
                            order.mpesa_transaction_date = kenya_tz.localize(naive_datetime)
                        except ValueError:
                            pass

                    order.save()

                    # Create payment confirmed tracking status
                    OrderTrackingStatus.objects.create(
                        order=order,
                        status='payment_confirmed',
                        message=f'M-Pesa payment confirmed. Receipt: {receipt_number}'
                    )

                    # Send confirmation email now that payment is successful
                    try:
                        if order.auto_created_account:
                            # Send payment confirmation with account details
                            OrderTrackingEmailService.send_payment_confirmation_email(order, None)
                        else:
                            # Send regular order confirmation
                            OrderTrackingEmailService.send_regular_order_confirmation(order, None)
                    except Exception as e:
                        logger.error(f"Failed to send confirmation email for order {order.id}: {str(e)}")

                    logger.info(f"M-Pesa payment successful for order {order.id}: {receipt_number}")

                else:
                    # Payment failed
                    order.payment_status = 'failed'
                    order.save()

                    # Create failed payment tracking status
                    OrderTrackingStatus.objects.create(
                        order=order,
                        status='cancelled',
                        message=f'M-Pesa payment failed: {result_desc}'
                    )

                    # Send failed payment notification email
                    try:
                        OrderTrackingEmailService.send_payment_failed_notification(
                            order=order,
                            failure_reason=result_desc,
                            request=None  # No request context in callback
                        )
                        logger.info(f"Failed payment notification sent for order {order.id}")
                    except Exception as e:
                        logger.error(f"Failed to send payment failure notification for order {order.id}: {str(e)}")

                    logger.warning(f"M-Pesa payment failed for order {order.id}: {result_desc}")

            except Order.DoesNotExist:
                logger.error(f"Order not found for M-Pesa callback: {checkout_request_id}")

        except Exception as e:
            logger.error(f"Error processing M-Pesa callback: {str(e)}")

    # Return success response to M-Pesa
    return JsonResponse({'ResultCode': 0, 'ResultDesc': 'Success'})


def how_it_works(request):
    """
    Interactive 'How It Works' page for administrators and app owners.
    Provides a comprehensive guide to the YummyTummy e-commerce system.
    """
    # Get some sample data for demonstration
    sample_products = Product.objects.filter(is_available=True)[:3]
    recent_orders = Order.objects.all().order_by('-created')[:5]

    # Calculate some basic statistics
    total_orders = Order.objects.count()
    completed_orders = Order.objects.filter(payment_status='completed').count()
    total_products = Product.objects.filter(is_available=True).count()

    context = {
        'sample_products': sample_products,
        'recent_orders': recent_orders,
        'stats': {
            'total_orders': total_orders,
            'completed_orders': completed_orders,
            'total_products': total_products,
            'conversion_rate': round((completed_orders / total_orders * 100) if total_orders > 0 else 0, 1)
        }
    }

    return render(request, 'yummytummy_store/admin/how_it_works.html', context)


@staff_member_required
def admin_dashboard(request):
    """
    Comprehensive admin dashboard with business insights and key metrics.
    Provides real-time data for store management and decision making.
    """
    # Get current date and time ranges for analytics
    now = timezone.now()
    today = now.date()
    week_start = today - timedelta(days=today.weekday())
    month_start = today.replace(day=1)

    # === SALES OVERVIEW ===
    # Total revenue calculations
    total_revenue = Order.objects.filter(payment_status='completed').aggregate(
        total=Sum('total_amount')
    )['total'] or 0

    revenue_today = Order.objects.filter(
        payment_status='completed',
        created__date=today
    ).aggregate(total=Sum('total_amount'))['total'] or 0

    revenue_this_week = Order.objects.filter(
        payment_status='completed',
        created__date__gte=week_start
    ).aggregate(total=Sum('total_amount'))['total'] or 0

    revenue_this_month = Order.objects.filter(
        payment_status='completed',
        created__date__gte=month_start
    ).aggregate(total=Sum('total_amount'))['total'] or 0

    # === ORDER MANAGEMENT ===
    # Order counts by status
    total_orders = Order.objects.count()
    completed_orders = Order.objects.filter(payment_status='completed').count()
    pending_orders = Order.objects.filter(payment_status='pending').count()
    processing_orders = Order.objects.filter(payment_status='processing').count()
    failed_orders = Order.objects.filter(payment_status='failed').count()

    # Orders requiring attention (pending or failed)
    orders_needing_attention = Order.objects.filter(
        payment_status__in=['pending', 'failed']
    ).count()

    # Recent orders (last 10)
    recent_orders = Order.objects.select_related('user').order_by('-created')[:10]

    # Orders today
    orders_today = Order.objects.filter(created__date=today).count()
    orders_this_week = Order.objects.filter(created__date__gte=week_start).count()
    orders_this_month = Order.objects.filter(created__date__gte=month_start).count()

    # === PRODUCT PERFORMANCE ===
    # Total active products
    total_products = Product.objects.filter(is_available=True).count()
    featured_products = Product.objects.filter(is_featured=True, is_available=True).count()

    # Best-selling products (by order item count)
    best_selling_products = OrderItem.objects.values(
        'product__name', 'product__id'
    ).annotate(
        total_sold=Sum('quantity'),
        total_revenue=Sum('price')
    ).order_by('-total_sold')[:5]

    # === CUSTOMER INSIGHTS ===
    # Customer statistics
    total_customers = User.objects.count()
    new_customers_today = User.objects.filter(date_joined__date=today).count()
    new_customers_this_week = User.objects.filter(date_joined__date__gte=week_start).count()
    new_customers_this_month = User.objects.filter(date_joined__date__gte=month_start).count()

    # Repeat customers (customers with more than one order)
    repeat_customers = User.objects.annotate(
        order_count=Count('orders')
    ).filter(order_count__gt=1).count()

    repeat_customer_rate = (repeat_customers / total_customers * 100) if total_customers > 0 else 0

    # === PAYMENT ANALYTICS ===
    # M-Pesa transaction success rate
    total_mpesa_attempts = Order.objects.filter(payment_method='mpesa').count()
    successful_mpesa = Order.objects.filter(
        payment_method='mpesa',
        payment_status='completed'
    ).count()

    mpesa_success_rate = (successful_mpesa / total_mpesa_attempts * 100) if total_mpesa_attempts > 0 else 0

    # Failed payments requiring follow-up
    failed_payments = Order.objects.filter(
        payment_status='failed',
        created__date__gte=today - timedelta(days=7)  # Last 7 days
    ).order_by('-created')[:5]

    # === BUSINESS METRICS ===
    # Average order value
    avg_order_value = Order.objects.filter(payment_status='completed').aggregate(
        avg=Avg('total_amount')
    )['avg'] or 0

    # Conversion rate (completed orders / total orders)
    conversion_rate = (completed_orders / total_orders * 100) if total_orders > 0 else 0

    # === RECENT ACTIVITY ===
    # Recent order tracking updates
    recent_tracking_updates = OrderTrackingStatus.objects.select_related(
        'order'
    ).order_by('-created_at')[:5]

    # === ALERTS & NOTIFICATIONS ===
    alerts = []

    # Low stock alerts (if you have inventory tracking)
    # alerts.append({'type': 'warning', 'message': 'Some products are running low on stock'})

    # Failed payments alert
    if failed_orders > 0:
        alerts.append({
            'type': 'danger',
            'message': f'{failed_orders} failed payments need attention'
        })

    # Pending orders alert
    if pending_orders > 5:
        alerts.append({
            'type': 'warning',
            'message': f'{pending_orders} orders are pending payment'
        })

    # New customers celebration
    if new_customers_today > 0:
        alerts.append({
            'type': 'success',
            'message': f'{new_customers_today} new customers joined today!'
        })

    context = {
        # Sales data
        'total_revenue': total_revenue,
        'revenue_today': revenue_today,
        'revenue_this_week': revenue_this_week,
        'revenue_this_month': revenue_this_month,

        # Order data
        'total_orders': total_orders,
        'completed_orders': completed_orders,
        'pending_orders': pending_orders,
        'processing_orders': processing_orders,
        'failed_orders': failed_orders,
        'orders_needing_attention': orders_needing_attention,
        'recent_orders': recent_orders,
        'orders_today': orders_today,
        'orders_this_week': orders_this_week,
        'orders_this_month': orders_this_month,

        # Product data
        'total_products': total_products,
        'featured_products': featured_products,
        'best_selling_products': best_selling_products,

        # Customer data
        'total_customers': total_customers,
        'new_customers_today': new_customers_today,
        'new_customers_this_week': new_customers_this_week,
        'new_customers_this_month': new_customers_this_month,
        'repeat_customers': repeat_customers,
        'repeat_customer_rate': round(repeat_customer_rate, 1),

        # Payment data
        'mpesa_success_rate': round(mpesa_success_rate, 1),
        'failed_payments': failed_payments,

        # Business metrics
        'avg_order_value': avg_order_value,
        'conversion_rate': round(conversion_rate, 1),

        # Recent activity
        'recent_tracking_updates': recent_tracking_updates,

        # Alerts
        'alerts': alerts,

        # Date context
        'today': today,
        'current_time': now,
    }

    return render(request, 'yummytummy_store/admin/dashboard.html', context)


def test_mpesa_auth(request):
    """
    Test M-Pesa authentication (for debugging only)
    """
    if not settings.DEBUG:
        return JsonResponse({'error': 'Not available in production'})

    try:
        mpesa_service = MPesaService()
        access_token = mpesa_service.get_access_token()

        if access_token:
            return JsonResponse({
                'success': True,
                'message': 'M-Pesa authentication successful',
                'token_length': len(access_token)
            })
        else:
            return JsonResponse({
                'success': False,
                'message': 'M-Pesa authentication failed'
            })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })
