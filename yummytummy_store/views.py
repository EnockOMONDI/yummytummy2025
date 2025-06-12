from django.shortcuts import render, get_object_or_404, redirect
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.contrib.auth import login, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db.models import Q
from django.urls import reverse
from django.utils.crypto import get_random_string
from django.utils import timezone
from django.http import JsonResponse
from .models import Category, Product, ProductVariant, Ingredient, Order, OrderItem, Coupon, CouponUsage, AutoCreatedAccount, OrderTrackingStatus
from .forms import CartAddProductForm, ProductSearchForm, ContactForm, CheckoutForm, PaymentForm, CouponApplyForm
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
                payment_status='processing',
                subtotal_amount=subtotal_amount,
                discount_amount=discount_amount,
                total_amount=total_amount,
                auto_created_account=bool(temp_password),  # Mark if account was auto-created
            )

            # Add M-Pesa phone number if applicable
            if payment_method == 'mpesa':
                order.mpesa_phone = form.cleaned_data['mpesa_phone']
                # Generate a random transaction ID for simulation
                order.transaction_id = f"MPESA{get_random_string(8).upper()}"

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

            # Create initial order tracking status
            OrderTrackingService.create_initial_tracking_status(order)

            # Send appropriate confirmation email
            try:
                if temp_password and auto_account:
                    # Send email with account creation details
                    email_sent = OrderTrackingEmailService.send_order_confirmation_with_account(
                        order, user_account, temp_password, auto_account, request
                    )
                else:
                    # Send regular order confirmation email
                    email_sent = OrderTrackingEmailService.send_regular_order_confirmation(
                        order, request
                    )

                if not email_sent:
                    messages.warning(request, "Order created successfully, but there was an issue sending the confirmation email.")

            except Exception as e:
                messages.warning(request, f"Order created successfully, but email could not be sent: {str(e)}")

            # Store order ID in session for confirmation page
            request.session['order_id'] = order.id

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
