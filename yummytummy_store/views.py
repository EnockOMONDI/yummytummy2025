from django.shortcuts import render, get_object_or_404, redirect
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.contrib.auth import login, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.admin.views.decorators import staff_member_required
from django.core.exceptions import ValidationError
from django.core import signing
from django.db import IntegrityError, connection, transaction
from django.db.models import Avg, Count, DecimalField, ExpressionWrapper, F, Q, Sum
from django.db.models.functions import TruncDate
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils.crypto import get_random_string
from django.utils import timezone
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation
from urllib.parse import quote
from .models import Category, Product, ProductVariant, Ingredient, Order, OrderItem, Coupon, CouponUsage, AutoCreatedAccount, NotificationOutbox, OrderTrackingStatus, Payment, PaymentAttempt, PaymentProviderEvent, RecipeCategory, Recipe, RecipeOrderItem, RecipePurchase
from .forms import CartAddProductForm, ProductSearchForm, ContactForm, CheckoutForm, PaymentForm, CouponApplyForm, CartAddRecipeForm, RecipeOnlyCheckoutForm, GuestCheckoutForm, MagicLinkRequestForm
from .mpesa_service import MPesaService
from .services import OrderTrackingEmailService, OrderTrackingService
from .payment_services import PaymentService

WHATSAPP_ORDER_PHONE = '254700061030'

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
def cart_add_recipe(request, recipe_id):
    """Add a recipe to the cart"""
    recipe = get_object_or_404(Recipe, id=recipe_id, is_published=True)
    form = CartAddRecipeForm(request.POST)

    if form.is_valid():
        # Initialize the cart in the session if it doesn't exist
        if 'cart' not in request.session:
            request.session['cart'] = {}

        # Get the cart from the session
        cart = request.session['cart']

        # Create a unique cart key for recipes
        cart_key = f"recipe_{recipe_id}"

        # Check if recipe is already in cart
        if cart_key in cart:
            messages.info(request, f'{recipe.title} is already in your cart.')
        else:
            # Add the recipe to the cart
            cart[cart_key] = {
                'recipe_id': recipe_id,
                'quantity': 1,  # Recipes are always quantity 1
                'price': str(recipe.price),
                'name': recipe.title,
                'type': 'recipe',  # Mark as recipe for cart processing
            }

            # Mark the session as modified to ensure it gets saved
            request.session.modified = True
            messages.success(request, f'{recipe.title} added to your cart.')

    else:
        # Add error messages for form validation failures
        for field, errors in form.errors.items():
            for error in errors:
                messages.error(request, f'Error in {field}: {error}')

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
    subtotal = Decimal('0.00')

    # Process cart items
    for cart_key, item_data in cart.items():
        try:
            price = Decimal(str(item_data['price']))
            quantity = int(item_data['quantity'])
            item_subtotal = price * quantity
            subtotal += item_subtotal

            # Check if this is a recipe or product
            item_type = item_data.get('type', 'product')  # Default to product for backward compatibility

            if item_type == 'recipe':
                # Handle recipe items
                recipe_id = item_data.get('recipe_id')
                recipe = None
                if recipe_id:
                    try:
                        recipe = Recipe.objects.get(id=recipe_id, is_published=True)
                    except Recipe.DoesNotExist:
                        continue

                cart_items.append({
                    'cart_key': cart_key,
                    'id': recipe_id,
                    'recipe': recipe,
                    'product': None,  # No product for recipes
                    'name': item_data['name'],
                    'variant_name': None,  # Recipes don't have variants
                    'price': price,
                    'quantity': quantity,
                    'subtotal': item_subtotal,
                    'type': 'recipe',
                })
            else:
                # Handle product items (existing logic)
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
                    'recipe': None,  # No recipe for products
                    'name': item_data['name'],
                    'variant_name': item_data.get('variant_name'),
                    'price': price,
                    'quantity': quantity,
                    'subtotal': item_subtotal,
                    'type': 'product',
                })
        except (InvalidOperation, ValueError, KeyError) as e:
            # Handle any corrupted cart data
            messages.error(request, f"Error processing cart item: {e}")
            continue

    # Get coupon from session if exists
    coupon_id = request.session.get('coupon_id')
    coupon = None
    discount = Decimal('0.00')

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
    cart_total = Decimal('0.00')
    for item_data in cart.values():
        try:
            price = Decimal(str(item_data['price']))
            quantity = int(item_data['quantity'])
            cart_total += price * quantity
        except (InvalidOperation, ValueError, KeyError):
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


def checkout_start(request):
    """Let shoppers choose guest checkout or account checkout for physical-product carts."""
    request.session.pop('retry_order_id', None)
    if 'cart' not in request.session or not request.session['cart']:
        messages.warning(request, "Your cart is empty. Please add some products before proceeding to checkout.")
        return redirect('yummytummy_store:product_list')

    has_products = False
    has_recipes = False
    for item_data in request.session['cart'].values():
        item_type = item_data.get('type', 'product')
        if item_type == 'recipe':
            has_recipes = True
        else:
            has_products = True

    if request.user.is_authenticated:
        request.session['checkout_mode'] = 'account'
        request.session.modified = True
        return redirect('yummytummy_store:checkout')

    if has_recipes:
        request.session['checkout_mode'] = 'account'
        request.session.modified = True
        return redirect('yummytummy_store:checkout')

    if request.method == 'POST':
        checkout_mode = request.POST.get('checkout_mode')
        if checkout_mode in ['guest', 'account', 'whatsapp']:
            request.session['checkout_mode'] = checkout_mode
            request.session.modified = True
            return redirect('yummytummy_store:checkout')

        messages.error(request, "Please choose how you would like to checkout.")

    return render(request, 'yummytummy_store/checkout/start.html', {
        'has_products': has_products,
        'has_recipes': has_recipes,
    })


def checkout(request):
    """Checkout page with conditional form based on cart contents"""
    # Check if cart is empty
    if 'cart' not in request.session or not request.session['cart']:
        messages.warning(request, "Your cart is empty. Please add some products before proceeding to checkout.")
        return redirect('yummytummy_store:product_list')

    # Process cart items and analyze cart contents
    cart = request.session['cart']
    cart_items = []
    subtotal = Decimal('0.00')
    has_products = False
    has_recipes = False

    for cart_key, item_data in cart.items():
        try:
            price = Decimal(str(item_data['price']))
            quantity = int(item_data['quantity'])
            item_subtotal = price * quantity
            subtotal += item_subtotal

            # Check item type
            item_type = item_data.get('type', 'product')  # Default to product for backward compatibility
            if item_type == 'recipe':
                has_recipes = True
            else:
                has_products = True

            cart_items.append({
                'cart_key': cart_key,
                'id': item_data.get('product_id') if item_type == 'product' else item_data.get('recipe_id'),
                'name': item_data['name'],
                'variant_name': item_data.get('variant_name'),
                'price': price,
                'quantity': quantity,
                'subtotal': item_subtotal,
                'type': item_type,
            })
        except (InvalidOperation, ValueError, KeyError) as e:
            messages.error(request, f"Error processing cart item: {e}")
            continue

    # Determine checkout type
    is_recipe_only = has_recipes and not has_products
    is_mixed_order = has_recipes and has_products
    checkout_mode = request.session.get('checkout_mode')
    if request.user.is_authenticated:
        checkout_mode = 'account'
        request.session['checkout_mode'] = checkout_mode
    elif not checkout_mode and not is_recipe_only and not is_mixed_order:
        return redirect('yummytummy_store:checkout_start')

    is_guest_checkout = checkout_mode in ['guest', 'whatsapp'] and not is_recipe_only and not is_mixed_order
    is_whatsapp_checkout = checkout_mode == 'whatsapp' and not is_recipe_only and not is_mixed_order

    # Get coupon from session if exists
    coupon_id = request.session.get('coupon_id')
    coupon = None
    discount = Decimal('0.00')

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
        # Use appropriate form based on cart contents
        if is_guest_checkout:
            form = GuestCheckoutForm(request.POST)
        elif is_recipe_only:
            form = RecipeOnlyCheckoutForm(request.POST)
        else:
            form = CheckoutForm(request.POST)

        if form.is_valid():
            # Store checkout data in session for payment step
            checkout_data = form.cleaned_data

            # Base checkout data
            session_data = {
                'first_name': checkout_data.get('first_name', 'Guest'),
                'last_name': checkout_data.get('last_name', 'Customer'),
                'email': checkout_data.get('email', ''),
                'phone': checkout_data.get('phone', ''),
                'order_notes': checkout_data.get('order_notes', ''),
                'subtotal_amount': float(subtotal),
                'discount_amount': float(discount),
                'total_amount': float(total),
                'coupon_id': coupon_id,
                'is_recipe_only': is_recipe_only,
                'is_mixed_order': is_mixed_order,
                'checkout_mode': checkout_mode,
            }

            # Add shipping fields only for product orders
            if not is_recipe_only:
                session_data.update({
                    'phone': checkout_data['phone'],
                    'address': checkout_data['address'],
                    'area': checkout_data['area'],
                    'estate': checkout_data['estate'],
                    'building': checkout_data['building'],
                    'landmark': checkout_data['landmark'],
                })

            request.session['checkout_data'] = session_data
            request.session.modified = True

            if is_whatsapp_checkout:
                order = _create_checkout_order(
                    request=request,
                    checkout_data=session_data,
                    payment_method='whatsapp',
                    payment_status='pending',
                    requires_account=False,
                )
                _clear_checkout_session(request)
                messages.success(request, "Your WhatsApp order has been created. Send the pre-filled WhatsApp message to confirm it with our team.")
                return redirect(_build_whatsapp_order_url(order))

            return redirect('yummytummy_store:payment')
    else:
        # Use appropriate form based on cart contents
        if is_guest_checkout:
            form = GuestCheckoutForm()
        elif is_recipe_only:
            form = RecipeOnlyCheckoutForm()
        else:
            form = CheckoutForm()

    context = {
        'form': form,
        'cart_items': cart_items,
        'subtotal': subtotal,
        'discount': discount,
        'total': total,
        'coupon': coupon,
        'is_recipe_only': is_recipe_only,
        'is_mixed_order': is_mixed_order,
        'has_products': has_products,
        'has_recipes': has_recipes,
        'checkout_mode': checkout_mode,
        'is_guest_checkout': is_guest_checkout,
        'is_whatsapp_checkout': is_whatsapp_checkout,
    }
    return render(request, 'yummytummy_store/checkout/shipping.html', context)


def _resolve_checkout_user(request, checkout_data, requires_account):
    """Return the user and whether a passwordless account was created."""
    if request.user.is_authenticated:
        return request.user, False

    if not requires_account:
        return None, False

    existing_user = User.objects.filter(email=checkout_data['email']).first()
    if existing_user:
        return existing_user, False

    return OrderTrackingEmailService.create_user_account(checkout_data)


@transaction.atomic
def _create_checkout_order(request, checkout_data, payment_method, payment_status='pending', requires_account=False, mpesa_phone=''):
    """Create an order from authoritative database prices in one transaction."""
    user_account, account_created = _resolve_checkout_user(request, checkout_data, requires_account)
    cart = request.session.get('cart') or {}
    if not cart:
        raise ValidationError('Your cart is empty.')

    product_items = []
    recipe_items = []
    subtotal = Decimal('0.00')

    for item_data in cart.values():
        try:
            quantity = int(item_data.get('quantity', 1))
        except (TypeError, ValueError):
            raise ValidationError('A cart item has an invalid quantity.')
        if quantity < 1 or quantity > 1000:
            raise ValidationError('Cart item quantities must be between 1 and 1,000.')

        if item_data.get('type') == 'recipe':
            quantity = 1
            if not user_account:
                raise ValidationError('Sign-in access is required for digital recipe purchases.')
            recipe = Recipe.objects.select_for_update().get(
                pk=item_data.get('recipe_id'),
                is_published=True,
            )
            unit_price = recipe.price
            recipe_items.append((recipe, quantity, unit_price))
        else:
            product = Product.objects.select_for_update().get(
                pk=item_data.get('product_id'),
                is_available=True,
            )
            variant = None
            variant_id = item_data.get('variant_id')
            if variant_id:
                variant = ProductVariant.objects.select_for_update().get(
                    pk=variant_id,
                    product=product,
                )
                unit_price = variant.calculated_price
                if product.track_inventory and variant.stock_quantity < quantity:
                    raise ValidationError(f'Only {variant.stock_quantity} units of {product.name} - {variant.name} are available.')
            else:
                unit_price = product.price
                if product.track_inventory and product.stock_quantity < quantity:
                    raise ValidationError(f'Only {product.stock_quantity} units of {product.name} are available.')
            product_items.append((product, variant, quantity, unit_price))

        subtotal += unit_price * quantity

    coupon = None
    discount = Decimal('0.00')
    coupon_id = checkout_data.get('coupon_id')
    if coupon_id:
        coupon = Coupon.objects.select_for_update().filter(pk=coupon_id, is_active=True).first()
        if coupon and coupon.is_valid(order_total=subtotal, user=user_account):
            discount = coupon.calculate_discount(subtotal).quantize(Decimal('0.01'))
        else:
            coupon = None

    order = Order.objects.create(
        user=user_account,
        first_name=checkout_data.get('first_name', 'Guest'),
        last_name=checkout_data.get('last_name', 'Customer'),
        email=checkout_data.get('email', ''),
        phone=checkout_data.get('phone', ''),
        address=checkout_data.get('address', ''),
        area=checkout_data.get('area', ''),
        estate=checkout_data.get('estate', ''),
        building=checkout_data.get('building', ''),
        landmark=checkout_data.get('landmark', ''),
        order_notes=checkout_data.get('order_notes', ''),
        payment_method=payment_method,
        payment_status=payment_status,
        mpesa_phone=mpesa_phone or '',
        subtotal_amount=subtotal,
        discount_amount=discount,
        total_amount=subtotal - discount,
        coupon=coupon,
        auto_created_account=account_created,
    )

    for product, variant, quantity, unit_price in product_items:
        OrderItem.objects.create(
            order=order,
            product=product,
            variant=variant,
            product_name=product.name,
            variant_name=variant.name if variant else '',
            price=unit_price,
            quantity=quantity,
        )
        if product.track_inventory:
            if variant:
                ProductVariant.objects.filter(pk=variant.pk).update(stock_quantity=F('stock_quantity') - quantity)
            else:
                Product.objects.filter(pk=product.pk).update(stock_quantity=F('stock_quantity') - quantity)

    for recipe, quantity, unit_price in recipe_items:
        RecipeOrderItem.objects.create(
            order=order,
            recipe=recipe,
            recipe_title=recipe.title,
            price=unit_price,
            quantity=quantity,
        )
    if coupon:
        Coupon.objects.filter(pk=coupon.pk).update(usage_count=F('usage_count') + 1)
        CouponUsage.objects.create(
            coupon=coupon,
            order=order,
            user=user_account,
            discount_amount=discount,
        )

    if account_created:
        auto_account = OrderTrackingEmailService.create_auto_account_record(user_account, order)
        request.session['pending_account_email'] = {
            'order_id': order.id,
            'user_id': user_account.id,
            'auto_account_id': auto_account.id,
        }
    elif order.email:
        request.session['pending_order_email'] = {'order_id': order.id}

    PaymentService.ensure_payment(order, payment_method)
    OrderTrackingService.create_initial_tracking_status(order)
    request.session['order_id'] = order.id

    from .services import CartPreservationService
    CartPreservationService.preserve_cart_for_order(order)

    request.session.modified = True
    return order


def _clear_checkout_session(request):
    """Clear cart and checkout state after an order is stored."""
    request.session['cart'] = {}
    for key in ['checkout_data', 'coupon_id', 'checkout_mode', 'retry_order_id']:
        if key in request.session:
            del request.session[key]
    request.session.modified = True


def _build_whatsapp_order_url(order):
    """Build a WhatsApp click-to-chat URL with pre-filled order details."""
    item_lines = []
    for item in order.items.all():
        variant = f" ({item.variant.name})" if item.variant else ""
        item_lines.append(f"- {item.quantity} x {item.product.name}{variant} @ KSh {item.price:,.2f}")

    delivery_parts = [
        order.address,
        order.area,
        order.estate,
        order.building,
        f"Near {order.landmark}" if order.landmark else "",
    ]
    delivery_address = ", ".join(part for part in delivery_parts if part)

    message = "\n".join([
        "Hello YummyTummy, I would like to place a WhatsApp order.",
        "",
        f"Order: {order.get_order_number()}",
        f"Customer: {order.first_name} {order.last_name}",
        f"Phone: {order.phone}",
        f"Delivery: {delivery_address}",
        "",
        "Items:",
        *item_lines,
        "",
        f"Subtotal: KSh {order.subtotal_amount:,.2f}",
        f"Discount: KSh {order.discount_amount:,.2f}",
        f"Total: KSh {order.total_amount:,.2f}",
        "",
        f"Notes: {order.order_notes}" if order.order_notes else "Notes: None",
    ])

    return f"https://api.whatsapp.com/send?phone={WHATSAPP_ORDER_PHONE}&text={quote(message)}"




def payment(request):
    """Create an order from server-side prices and initiate its selected payment."""
    checkout_data = request.session.get('checkout_data')
    cart = request.session.get('cart')
    if not checkout_data:
        messages.warning(request, 'Please complete the shipping information first.')
        return redirect('yummytummy_store:checkout')
    if not cart:
        messages.warning(request, 'Your cart is empty.')
        return redirect('yummytummy_store:product_list')

    if request.method == 'POST':
        form = PaymentForm(request.POST)
        if form.is_valid():
            method = form.cleaned_data['payment_method']
            payment_record = None
            retry_order_id = request.session.get('retry_order_id')
            if retry_order_id:
                try:
                    order = Order.objects.get(pk=retry_order_id, payment_status='failed')
                except Order.DoesNotExist:
                    request.session.pop('retry_order_id', None)
                    form.add_error(None, 'This order is no longer eligible for payment retry.')
                else:
                    order.mpesa_phone = form.cleaned_data.get('mpesa_phone', '')
                    order.save(update_fields=['mpesa_phone', 'updated'])
                    payment_record = PaymentService.ensure_payment(order, method)
            else:
                requires_account = (
                    checkout_data.get('is_recipe_only')
                    or checkout_data.get('is_mixed_order')
                    or checkout_data.get('checkout_mode') == 'account'
                )
                try:
                    order = _create_checkout_order(
                        request=request,
                        checkout_data=checkout_data,
                        payment_method=method,
                        requires_account=requires_account,
                        mpesa_phone=form.cleaned_data.get('mpesa_phone', ''),
                    )
                except (ValidationError, Product.DoesNotExist, ProductVariant.DoesNotExist, Recipe.DoesNotExist) as exc:
                    message = exc.messages[0] if isinstance(exc, ValidationError) else 'A cart item is no longer available.'
                    form.add_error(None, message)
                except IntegrityError:
                    form.add_error(None, 'The order could not be created safely. Please review your cart and try again.')
                else:
                    payment_record = order.payments.get(is_current=True)

            if payment_record and not form.errors:
                if method == 'mpesa':
                    attempt = PaymentService.create_attempt(payment_record)
                    if (
                        (settings.DEBUG or getattr(settings, 'TESTING', False))
                        and not getattr(settings, 'MPESA_ALLOW_LIVE_IN_DEBUG', False)
                    ):
                        PaymentService.mark_failed(attempt, 'debug_live_disabled', 'Live M-Pesa calls are disabled in development.')
                        messages.error(request, 'Live M-Pesa requests are disabled in local development.')
                    else:
                        try:
                            mpesa_response = MPesaService().initiate_stk_push(
                                phone_number=order.mpesa_phone,
                                amount=float(order.total_amount),
                                order_id=order.id,
                                callback_url=settings.MPESA_CALLBACK_URL,
                            )
                        except Exception as exc:
                            mpesa_response = {
                                'success': False,
                                'error': 'The payment provider could not be reached.',
                                'error_code': exc.__class__.__name__,
                            }

                        if mpesa_response.get('success'):
                            PaymentService.mark_submitted(
                                attempt,
                                mpesa_response.get('checkout_request_id'),
                                mpesa_response.get('merchant_request_id', ''),
                            )
                            messages.success(request, 'M-Pesa payment initiated. Check your phone for the prompt.')
                        else:
                            PaymentService.mark_failed(
                                attempt,
                                mpesa_response.get('error_code', ''),
                                mpesa_response.get('error', 'Payment initiation failed.'),
                            )
                            OrderTrackingStatus.objects.create(
                                order=order,
                                status='payment_failed',
                                message='M-Pesa payment could not be initiated. The customer can retry payment.',
                            )
                            messages.error(request, 'M-Pesa could not be initiated. Please retry or choose another payment method.')

                request.session['order_id'] = order.id
                _clear_checkout_session(request)
                return redirect('yummytummy_store:order_confirmation')
    else:
        form = PaymentForm()

    context = {
        'form': form,
        'checkout_data': checkout_data,
        'subtotal_amount': checkout_data.get('subtotal_amount', 0),
        'discount_amount': checkout_data.get('discount_amount', 0),
        'total_amount': checkout_data.get('total_amount', 0),
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
        recipe_order_items = order.recipe_items.all()
    except Order.DoesNotExist:
        messages.error(request, "Order not found.")
        return redirect('yummytummy_store:product_list')

    # Clear order ID from session after displaying confirmation
    del request.session['order_id']
    request.session.modified = True

    context = {
        'order': order,
        'order_items': order_items,
        'recipe_order_items': recipe_order_items,
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

        messages.success(request, f"Welcome to YummyTummy, {auto_account.user.first_name}! You are signed in securely.")

        # Redirect to order tracking dashboard
        return redirect('yummytummy_store:order_tracking_dashboard')

    except AutoCreatedAccount.DoesNotExist:
        messages.error(request, "Invalid or expired login link. Please contact support for assistance.")
        return redirect('yummytummy_store:home')


def request_magic_link(request):
    """Send a passwordless sign-in link without revealing whether an account exists."""
    initial_email = request.GET.get('email', '')
    form = MagicLinkRequestForm(request.POST or None, initial={'email': initial_email})
    next_url = request.POST.get('next', request.GET.get('next', ''))

    if request.method == 'POST' and form.is_valid():
        now_timestamp = int(timezone.now().timestamp())
        last_request = request.session.get('magic_link_requested_at', 0)
        if now_timestamp - last_request >= 60:
            user = User.objects.filter(
                email__iexact=form.cleaned_data['email'],
                is_active=True,
            ).order_by('pk').first()
            if user:
                OrderTrackingEmailService.send_magic_login_link(user, request, next_url=next_url)
            request.session['magic_link_requested_at'] = now_timestamp
            request.session.modified = True

        messages.success(request, 'If that email belongs to an active account, a secure sign-in link has been sent.')
        return redirect('yummytummy_store:request_magic_link')

    return render(request, 'registration/magic_link_request.html', {
        'form': form,
        'next': next_url,
    })


def magic_link_login(request, token):
    """Consume a timestamped magic link and log the account in once."""
    try:
        payload = signing.loads(token, salt='yummytummy.magic-login', max_age=900)
    except signing.BadSignature:
        messages.error(request, 'This sign-in link is invalid or has expired. Request a new link.')
        return redirect('yummytummy_store:request_magic_link')

    with transaction.atomic():
        user = User.objects.select_for_update().filter(
            pk=payload.get('user_id'),
            email__iexact=payload.get('email', ''),
            is_active=True,
        ).first()
        marker = user.last_login.isoformat() if user and user.last_login else ''
        if not user or marker != payload.get('login_marker', ''):
            messages.error(request, 'This sign-in link has already been used or is no longer valid.')
            return redirect('yummytummy_store:request_magic_link')
        login(request, user)

    next_url = payload.get('next', '')
    if not url_has_allowed_host_and_scheme(
        url=next_url,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        next_url = reverse('yummytummy_store:order_tracking_dashboard')
    messages.success(request, 'You are now signed in.')
    return redirect(next_url)


@login_required
def order_tracking_dashboard(request):
    """User dashboard for viewing order history and tracking"""
    # Get user's orders
    orders = Order.objects.filter(user=request.user).order_by('-created')

    # Get order tracking information
    orders_with_tracking = []
    processing_orders = 0
    delivered_orders = 0
    for order in orders:
        latest_status = order.get_latest_tracking_status()
        progress_percentage = OrderTrackingService.get_order_progress_percentage(order)
        status = latest_status.status if latest_status else 'processing'
        processing_orders += status == 'processing'
        delivered_orders += status == 'delivered'

        orders_with_tracking.append({
            'order': order,
            'latest_status': latest_status,
            'progress_percentage': progress_percentage,
            'tracking_history': order.tracking_statuses.all()[:3],  # Show last 3 updates
            'item_count': order.items.count() + order.recipe_items.count(),
        })

    context = {
        'orders_with_tracking': orders_with_tracking,
        'processing_orders': processing_orders,
        'delivered_orders': delivered_orders,
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
    for item in order.recipe_items.all():
        order_items.append({
            'recipe': item.recipe,
            'variant': None,
            'quantity': item.quantity,
            'price': item.price,
            'total': item.get_cost(),
            'display_name': item.recipe_title or item.recipe.title,
            'is_digital': True,
        })

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
        contact = request.POST.get('contact', '').strip()

        if order_number and contact:
            try:
                # Extract order ID from order number (format: MSL-000123)
                if order_number.startswith('MSL-'):
                    order_id = int(order_number.split('-')[1])
                    order = Order.objects.get(
                        Q(email__iexact=contact) | Q(phone=contact) | Q(mpesa_phone=contact),
                        id=order_id
                    )

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
                    for item in order.recipe_items.all():
                        order_items.append({
                            'recipe': item.recipe,
                            'variant': None,
                            'quantity': item.quantity,
                            'price': item.price,
                            'total': item.get_cost(),
                            'display_name': item.recipe_title or item.recipe.title,
                            'is_digital': True,
                        })

                    context = {
                        'order': order,
                        'order_items': order_items,
                        'tracking_history': tracking_history,
                        'progress_percentage': progress_percentage,
                        'is_guest_tracking': True,
                    }
                    if order.payment_status == 'failed':
                        retry_token = signing.dumps(
                            {'order_id': order.pk, 'email': order.email},
                            salt='yummytummy.payment-retry',
                            compress=True,
                        )
                        retry_path = reverse('yummytummy_store:payment_retry', args=[order.pk])
                        context['payment_retry_url'] = f'{retry_path}?token={quote(retry_token)}'
                    return render(request, 'yummytummy_store/account/guest_order_tracking.html', context)
                else:
                    error_message = "Invalid order number format. Order numbers start with 'MSL-'"
            except (ValueError, Order.DoesNotExist):
                error_message = "Order not found. Please check your order number and phone or email."
        else:
            error_message = "Please enter both order number and phone or email."

    context = {
        'order': order,
        'error_message': error_message,
    }
    return render(request, 'yummytummy_store/account/guest_order_tracking.html', context)


def payment_retry(request, order_id):
    """Allow customers to retry payment for failed orders"""
    try:
        order = get_object_or_404(Order, id=order_id, payment_status='failed')

        authorized_user = (
            request.user.is_authenticated
            and (request.user.is_staff or order.user_id == request.user.id)
        )
        if not authorized_user:
            try:
                token_data = signing.loads(
                    request.GET.get('token', ''),
                    salt='yummytummy.payment-retry',
                    max_age=7 * 24 * 60 * 60,
                )
                authorized_user = (
                    token_data.get('order_id') == order.pk
                    and token_data.get('email', '').casefold() == order.email.casefold()
                )
            except (signing.BadSignature, signing.SignatureExpired, AttributeError):
                authorized_user = False

        if not authorized_user:
            messages.error(request, 'Use the secure retry link from your payment email or track your order first.')
            return redirect('yummytummy_store:guest_order_tracking')

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
                'checkout_mode': 'account' if order.user_id else 'guest',
            }
            request.session['retry_order_id'] = order.id
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
@require_POST
def mpesa_callback(request):
    """Process an M-Pesa callback with event idempotency and strict correlation."""
    import json
    import logging
    from zoneinfo import ZoneInfo

    logger = logging.getLogger(__name__)
    if len(request.body) > 64 * 1024:
        return JsonResponse({'ResultCode': 1, 'ResultDesc': 'Payload too large'}, status=413)

    try:
        payload = json.loads(request.body.decode('utf-8'))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse({'ResultCode': 1, 'ResultDesc': 'Invalid JSON payload'}, status=400)

    callback = payload.get('Body', {}).get('stkCallback', {}) if isinstance(payload, dict) else {}
    checkout_request_id = callback.get('CheckoutRequestID')
    merchant_request_id = callback.get('MerchantRequestID')
    result_code = callback.get('ResultCode')
    result_desc = str(callback.get('ResultDesc', 'Payment failed'))[:160]
    if not checkout_request_id or result_code is None:
        return JsonResponse({'ResultCode': 1, 'ResultDesc': 'Missing callback identifiers'}, status=400)
    try:
        result_code = int(result_code)
    except (TypeError, ValueError):
        return JsonResponse({'ResultCode': 1, 'ResultDesc': 'Invalid result code'}, status=400)

    metadata = {}
    callback_metadata = callback.get('CallbackMetadata') or {}
    for item in callback_metadata.get('Item', []) if isinstance(callback_metadata, dict) else []:
        if isinstance(item, dict) and item.get('Name'):
            metadata[item['Name']] = item.get('Value')
    receipt_number = str(metadata.get('MpesaReceiptNumber', ''))

    event, created = PaymentService.record_provider_event(
        payload,
        checkout_request_id,
        result_code,
        receipt_number,
    )
    with transaction.atomic():
        event = PaymentProviderEvent.objects.select_for_update().get(pk=event.pk)
        # A persisted event may still need processing after a previous transaction failed.
        if event.processing_status != 'received':
            return JsonResponse({'ResultCode': 0, 'ResultDesc': 'Callback already processed'})
        attempt = (
            PaymentAttempt.objects.select_for_update()
            .select_related('payment__order')
            .filter(checkout_request_id=checkout_request_id)
            .first()
        )
        if not attempt:
            event.processing_status = 'ignored'
            event.failure_reason = 'No matching payment attempt.'
            event.processed_at = timezone.now()
            event.save(update_fields=['processing_status', 'failure_reason', 'processed_at'])
            logger.warning('Ignored unmatched M-Pesa callback %s', event.pk)
            return JsonResponse({'ResultCode': 0, 'ResultDesc': 'Callback acknowledged'})

        payment_record = attempt.payment
        order = payment_record.order
        event.payment = payment_record
        event.attempt = attempt

        if payment_record.method != 'mpesa':
            event.processing_status = 'failed'
            event.failure_reason = 'Payment method mismatch.'
        elif payment_record.status in {'succeeded', 'partially_refunded', 'refunded'}:
            event.processing_status = 'ignored'
            event.failure_reason = 'Payment was already finalized.'
        elif attempt.merchant_request_id and merchant_request_id != attempt.merchant_request_id:
            event.processing_status = 'failed'
            event.failure_reason = 'Merchant request ID mismatch.'
        elif result_code == 0:
            amount = PaymentService.parse_amount(metadata.get('Amount'))
            duplicate_receipt = Payment.objects.exclude(pk=payment_record.pk).filter(
                method='mpesa',
                provider_reference=receipt_number,
            ).exists()
            if not receipt_number:
                event.processing_status = 'failed'
                event.failure_reason = 'Successful callback did not include a receipt number.'
            elif amount != payment_record.amount:
                event.processing_status = 'failed'
                event.failure_reason = 'Callback amount does not match the payment amount.'
            elif duplicate_receipt:
                event.processing_status = 'failed'
                event.failure_reason = 'Receipt number is already assigned to another payment.'
            else:
                completed_at = timezone.now()
                transaction_date = metadata.get('TransactionDate')
                if transaction_date:
                    try:
                        completed_at = datetime.strptime(str(transaction_date), '%Y%m%d%H%M%S').replace(
                            tzinfo=ZoneInfo('Africa/Nairobi')
                        )
                    except (TypeError, ValueError):
                        pass

                PaymentService.mark_succeeded(attempt, receipt_number, completed_at)
                order.mpesa_receipt_number = receipt_number
                order.mpesa_transaction_date = completed_at
                order.save(update_fields=['mpesa_receipt_number', 'mpesa_transaction_date', 'updated'])
                OrderTrackingStatus.objects.create(
                    order=order,
                    status='payment_confirmed',
                    message='M-Pesa payment confirmed.',
                )
                from .notifications import NotificationService
                NotificationService.enqueue_payment_result(order, succeeded=True)
                event.processing_status = 'processed'
        else:
            PaymentService.mark_failed(attempt, result_code, result_desc)
            OrderTrackingStatus.objects.create(
                order=order,
                status='payment_failed',
                message='M-Pesa payment was not completed. The customer can retry payment.',
            )
            from .notifications import NotificationService
            NotificationService.enqueue_payment_result(order, succeeded=False, failure_reason=result_desc)
            event.processing_status = 'processed'

        event.processed_at = timezone.now()
        event.save(update_fields=[
            'payment', 'attempt', 'processing_status', 'failure_reason', 'processed_at'
        ])

    return JsonResponse({'ResultCode': 0, 'ResultDesc': 'Success'})




@staff_member_required
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
    except Exception:
        return JsonResponse({
            'success': False,
            'error': 'M-Pesa authentication check failed.'
        })


# ================================================================
# RECIPE VIEWS
# ================================================================

def recipe_list(request):
    """View for displaying all published recipes"""
    recipes = Recipe.objects.filter(is_published=True).select_related('category')
    categories = RecipeCategory.objects.all()

    # Filter by category if specified
    category_slug = request.GET.get('category')
    if category_slug:
        category = get_object_or_404(RecipeCategory, slug=category_slug)
        recipes = recipes.filter(category=category)
    else:
        category = None

    # Filter by search query
    search_query = request.GET.get('search')
    if search_query:
        recipes = recipes.filter(
            Q(title__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(tags__icontains=search_query)
        )

    # Filter by difficulty
    difficulty = request.GET.get('difficulty')
    if difficulty and difficulty in ['easy', 'medium', 'hard']:
        recipes = recipes.filter(difficulty=difficulty)

    # Order recipes
    order_by = request.GET.get('order_by', '-created')
    if order_by in ['title', '-title', 'price', '-price', 'created', '-created', 'prep_time_minutes', '-prep_time_minutes']:
        recipes = recipes.order_by(order_by)

    # Get featured recipes
    featured_recipes = Recipe.objects.filter(is_published=True, is_featured=True)[:3]

    context = {
        'recipes': recipes,
        'categories': categories,
        'current_category': category,
        'featured_recipes': featured_recipes,
        'search_query': search_query,
        'current_difficulty': difficulty,
        'current_order': order_by,
    }

    return render(request, 'yummytummy_store/recipe/list.html', context)


def recipe_detail(request, slug):
    """View for displaying a single recipe"""
    recipe = get_object_or_404(Recipe, slug=slug, is_published=True)

    # Check if user has purchased this recipe
    user_has_purchased = False
    if request.user.is_authenticated:
        user_has_purchased = RecipePurchase.objects.filter(
            user=request.user,
            recipe=recipe
        ).exists()

    # Get related recipes from the same category
    related_recipes = Recipe.objects.filter(
        category=recipe.category,
        is_published=True
    ).exclude(id=recipe.id)[:3]

    # Get cart form for adding recipe to cart
    cart_form = CartAddRecipeForm()

    context = {
        'recipe': recipe,
        'user_has_purchased': user_has_purchased,
        'related_recipes': related_recipes,
        'cart_form': cart_form,
    }

    return render(request, 'yummytummy_store/recipe/detail.html', context)


@login_required
def recipe_download(request, slug):
    """View for downloading purchased recipe PDF"""
    recipe = get_object_or_404(Recipe, slug=slug, is_published=True)

    # Check if user has purchased this recipe
    try:
        purchase = RecipePurchase.objects.get(user=request.user, recipe=recipe)
    except RecipePurchase.DoesNotExist:
        messages.error(request, "You haven't purchased this recipe yet.")
        return redirect('yummytummy_store:recipe_detail', slug=slug)

    # Increment download count
    purchase.download_count += 1
    purchase.save()

    # Check if PDF file exists, generate if missing
    if not recipe.pdf_file:
        try:
            # Try to generate PDF on-demand
            from .pdf_utils import generate_recipe_pdf
            pdf_file = generate_recipe_pdf(recipe)
            recipe.pdf_file.save(pdf_file.name, pdf_file, save=True)
            messages.success(request, "Recipe PDF generated successfully.")
        except Exception as e:
            messages.error(request, "Recipe PDF is not available for download.")
            return redirect('yummytummy_store:recipe_detail', slug=slug)

    # Serve the PDF file
    from django.http import FileResponse

    try:
        response = FileResponse(
            recipe.pdf_file.open('rb'),
            as_attachment=True,
            filename=f"{recipe.title.replace(' ', '_')}_Recipe.pdf"
        )
        return response
    except Exception as e:
        messages.error(request, "Error downloading recipe. Please try again later.")
        return redirect('yummytummy_store:recipe_detail', slug=slug)


@login_required
def my_recipes(request):
    """View for displaying user's purchased recipes"""
    purchased_recipes = RecipePurchase.objects.filter(
        user=request.user
    ).select_related('recipe', 'recipe__category').order_by('-purchased_at')

    context = {
        'purchased_recipes': purchased_recipes,
    }

    return render(request, 'yummytummy_store/recipe/my_recipes.html', context)
