# YummyTummy E-commerce System - Business Operations & Customer Experience Guide

**Version**: 2.0
**Last Updated**: December 13, 2025
**Target Audience**: Business owners, administrators, and operational staff

---

## 📋 Table of Contents

1. [Business Overview & System Capabilities](#business-overview--system-capabilities)
2. [Customer Journey & Experience](#customer-journey--experience)
3. [Order Management & Processing](#order-management--processing)
4. [Payment System & Security](#payment-system--security)
5. [Customer Account Management](#customer-account-management)
6. [Communication & Notifications](#communication--notifications)
7. [Data Management & Analytics](#data-management--analytics)
8. [System Administration](#system-administration)
9. [Performance & Reliability](#performance--reliability)
10. [Business Growth Features](#business-growth-features)

---

## � Business Overview & System Capabilities

### **What YummyTummy Does for Your Business**
YummyTummy is a complete e-commerce solution designed specifically for Kenyan food businesses. It handles everything from product display to payment processing and customer management, allowing you to focus on your products while the system manages your online sales.

### **Core Business Capabilities**
- **🛍️ Product Management**: Easy-to-manage product catalog with multiple sizes and pricing
- **💳 Secure Payments**: Integrated M-Pesa payment processing for Kenyan customers
- **👥 Customer Management**: Automatic account creation and order tracking
- **📱 Mobile-First Design**: Optimized for mobile shopping (80% of Kenyan internet users)
- **📊 Order Processing**: Complete order lifecycle from cart to delivery
- **📧 Customer Communication**: Automated email notifications and updates
- **🎯 Business Intelligence**: Order analytics and customer insights

### **Technology Foundation**
- **Hosting**: Render.com (reliable cloud hosting)
- **Database**: Neon PostgreSQL (secure, scalable data storage)
- **Images**: Uploadcare CDN (fast, professional image delivery)
- **Payments**: Safaricom M-Pesa API (trusted mobile money integration)
- **Security**: HTTPS encryption, secure payment processing, GDPR compliance

### **Business Benefits**
- ✅ **Reduced Manual Work**: Automated order processing and customer communication
- ✅ **Increased Sales**: Mobile-optimized shopping experience
- ✅ **Better Customer Service**: Real-time order tracking and automated notifications
- ✅ **Professional Image**: High-quality product presentation and smooth checkout
- ✅ **Scalable Growth**: System grows with your business needs
- ✅ **Cost Effective**: All-in-one solution reduces need for multiple tools

---

## 🛤️ User Journey Flows

### **1. Homepage Browsing & Product Discovery**

#### **User Action**: Visit Homepage
**Technical Process**: 
- `GET /` → `views.home()` → Query featured products → Render template
- **Files**: `yummytummy_store/views.py:19-45`, `templates/home.html`
- **Database**: `Product.objects.filter(is_available=True)[:4]`

**Backend Response**: 
- Featured products loaded from database
- Hero section with highlighted product
- Product showcase with expandable variant cards

**Frontend Update**: 
- Homepage renders with product slider
- Cart count displays in navigation
- Expandable product cards ready for interaction

**Validation Status**: ✅ **WORKING**

---

#### **User Action**: Click "View Sizes" on Product Card
**Technical Process**: 
- JavaScript `expandCard()` function executes
- **Files**: `static/js/expandable-cards.js:45-67`
- DOM manipulation shows variant options
- Close other expanded cards

**Backend Response**: 
- No backend call (client-side only)

**Frontend Update**: 
- Card expands with smooth animation
- Variant options become visible
- Quantity selectors activated

**Validation Status**: ✅ **WORKING**

---

#### **User Action**: Select Product Variant & Add to Cart
**Technical Process**: 
- Form submission with variant data
- **Files**: `static/js/main.js:150-280`, `yummytummy_store/views.py:108-169`
- `POST /cart/add/<product_id>/` with form data:
  ```python
  {
      'quantity': 1,
      'update': False,
      'selected_variant': '<variant_id>'
  }
  ```

**Backend Response**: 
- `CartAddProductForm` validation
- Session cart updated with product/variant
- Success message added
- Redirect to cart page (302)

**Frontend Update**: 
- Flying animation (if enabled)
- Cart count increments
- Success message displays
- User redirected to cart

**Validation Status**: ✅ **WORKING** (Recently fixed)

---

### **2. Shopping Cart Management**

#### **User Action**: View Cart Contents
**Technical Process**: 
- `GET /cart/` → `views.cart_detail()` → Process session cart
- **Files**: `yummytummy_store/views.py:250-334`
- Database queries for product details:
  ```python
  for cart_key, item_data in cart.items():
      product = Product.objects.get(id=product_id)
  ```

**Backend Response**: 
- Cart items with product details
- Subtotal and discount calculations
- Coupon validation (if applied)

**Frontend Update**: 
- Cart table with product images
- Quantity selectors for each item
- Subtotal, discount, and total display
- Checkout button activation

**Validation Status**: ✅ **WORKING**

---

#### **User Action**: Update Item Quantity
**Technical Process**: 
- Form submission via quantity selector
- **Files**: `templates/cart/detail.html:38-45`, `views.py:196-226`
- `POST /cart/update/<cart_key>/` with new quantity

**Backend Response**: 
- Session cart updated
- New subtotal calculated
- Success message added

**Frontend Update**: 
- Page reload with updated quantities
- New totals displayed
- Success message shown

**Validation Status**: ✅ **WORKING**

---

### **3. Checkout Process**

#### **User Action**: Proceed to Checkout
**Technical Process**: 
- `GET /checkout/` → `views.checkout()` → Validate cart
- **Files**: `yummytummy_store/views.py:430-523`
- Cart validation and total calculation

**Backend Response**: 
- Checkout form rendered
- Cart summary displayed
- Coupon discounts applied

**Frontend Update**: 
- Shipping address form
- Order summary sidebar
- Form validation ready

**Validation Status**: ✅ **WORKING**

---

#### **User Action**: Submit Shipping Information
**Technical Process**: 
- `POST /checkout/` → `CheckoutForm` validation → Session storage
- **Files**: `yummytummy_store/forms.py:31-48`, `views.py:489-511`
- Form data stored in session for payment step

**Backend Response**: 
- Form validation
- Session data updated
- Redirect to payment page

**Frontend Update**: 
- User redirected to payment selection
- Shipping data preserved

**Validation Status**: ✅ **WORKING**

---

### **4. Payment Processing (M-Pesa)**

#### **User Action**: Select M-Pesa Payment & Submit
**Technical Process**: 
- `POST /checkout/payment/` → Account creation → M-Pesa initiation
- **Files**: `yummytummy_store/views.py:544-736`, `mpesa_service.py:98-194`

**Account Creation Flow**:
```python
# Check existing user
existing_user = User.objects.filter(email=email).first()
if not existing_user:
    # Create new account
    user, temp_password = OrderTrackingEmailService.create_user_account(data)
```

**M-Pesa Integration Flow**:
```python
# Initialize M-Pesa service
mpesa_service = MPesaService()
# STK Push request
response = mpesa_service.initiate_stk_push(
    phone_number=order.mpesa_phone,
    amount=float(order.total_amount),
    order_id=order.id,
    callback_url=callback_url
)
```

**Backend Response**: 
- Order created in database
- User account created (if new)
- M-Pesa STK Push initiated
- Order tracking status created

**Frontend Update**: 
- Success message displayed
- User redirected to confirmation
- Cart cleared from session

**Validation Status**: ✅ **WORKING**

---

#### **M-Pesa Callback Processing**
**Technical Process**: 
- `POST /mpesa/callback/` → `views.mpesa_callback()` → Order update
- **Files**: `yummytummy_store/views.py:888-976`

**Callback Data Processing**:
```python
# Parse M-Pesa callback
callback_data = json.loads(request.body)
stk_callback = callback_data.get('Body', {}).get('stkCallback', {})
result_code = stk_callback.get('ResultCode')

if result_code == 0:  # Success
    order.payment_status = 'completed'
    order.transaction_id = receipt_number
```

**Backend Response**: 
- Order payment status updated
- Transaction details stored
- Order tracking status created

**Validation Status**: ✅ **WORKING**

---

### **5. Order Tracking & Account Management**

#### **User Action**: First-Time Login via Email Link
**Technical Process**: 
- `GET /first-login/<token>/` → Token validation → Auto-login
- **Files**: `yummytummy_store/views.py:759-806`

**Token Validation**:
```python
auto_account = AutoCreatedAccount.objects.get(
    first_login_token=token,
    token_expires__gt=timezone.now()
)
# Auto-login user
login(request, auto_account.user)
```

**Backend Response**: 
- Token validated
- User automatically logged in
- Redirect to dashboard

**Frontend Update**: 
- User logged in
- Dashboard accessible
- Order history visible

**Validation Status**: ✅ **WORKING**

---

#### **User Action**: View Order History
**Technical Process**: 
- `GET /account/dashboard/` → `views.order_tracking_dashboard()` → Order query
- **Files**: `yummytummy_store/views.py:808-829`

**Database Query**:
```python
orders = Order.objects.filter(user=request.user).order_by('-created')
for order in orders:
    latest_status = order.get_latest_tracking_status()
    progress_percentage = OrderTrackingService.get_order_progress_percentage(order)
```

**Backend Response**: 
- User's orders with tracking info
- Progress percentages calculated
- Latest status for each order

**Frontend Update**: 
- Order cards with status
- Progress bars
- Order details links

**Validation Status**: ✅ **WORKING**

---

## 🔧 Backend Components & Models

### **Core Models** (`yummytummy_store/models.py`)

#### **Product Model** (Lines 48-90)
```python
class Product(models.Model):
    category = models.ForeignKey(Category, related_name='products', on_delete=models.CASCADE)
    name = models.CharField(max_length=200)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    image = ImageField(blank=True, manual_crop="")  # Uploadcare integration
    is_available = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)
```

#### **ProductVariant Model** (Lines 93-120)
```python
class ProductVariant(models.Model):
    product = models.ForeignKey(Product, related_name='variants', on_delete=models.CASCADE)
    name = models.CharField(max_length=100)  # e.g., "500g", "1kg"
    additional_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    is_active = models.BooleanField(default=True)
```

#### **Order Model** (Lines 123-268)
```python
class Order(models.Model):
    user = models.ForeignKey(User, related_name='orders', on_delete=models.CASCADE, null=True, blank=True)
    # Customer information
    first_name = models.CharField(max_length=50)
    email = models.EmailField()
    phone = models.CharField(max_length=20)
    # Address fields
    address = models.CharField(max_length=250)
    area = models.CharField(max_length=100, blank=True)
    # Payment information
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES)
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='pending')
    # M-Pesa specific fields
    mpesa_phone = models.CharField(max_length=20, blank=True)
    mpesa_checkout_request_id = models.CharField(max_length=100, blank=True)
    transaction_id = models.CharField(max_length=100, blank=True)
```

### **Business Services** (`yummytummy_store/services.py`)

#### **OrderTrackingEmailService** (Lines 18-168)
- **Purpose**: Handle automatic account creation and email notifications
- **Key Methods**:
  - `create_user_account()`: Creates user from order data
  - `send_order_confirmation_with_account()`: Sends welcome email with login credentials
  - `generate_secure_password()`: Creates secure temporary passwords

#### **OrderTrackingService** (Lines 170-220)
- **Purpose**: Manage order status progression and tracking
- **Key Methods**:
  - `create_initial_tracking_status()`: Sets up initial order tracking
  - `get_order_progress_percentage()`: Calculates completion percentage

---

## 🎨 Frontend Components & Templates

### **Template Structure** (`yummytummy_store/templates/`)

#### **Base Template** (`base.html`)
- **Navigation**: Main menu, cart count, user authentication status
- **Header**: Logo, search, mobile menu toggle
- **Footer**: Contact information, social links
- **Messages**: Django messages display system

#### **Homepage** (`home.html`)
- **Hero Section**: Featured product with variant expansion
- **Product Showcase**: Expandable cards with variant selection
- **About Section**: Brand story and process steps

#### **Cart Template** (`cart/detail.html`)
- **Cart Table**: Product details, quantities, prices
- **Quantity Controls**: Plus/minus buttons with form submission
- **Coupon System**: Apply/remove discount codes
- **Checkout Button**: Proceed to shipping form

### **CSS Architecture** (`static/yummytummy_store/css/styles.css`)

#### **CSS Variables** (Lines 1-12)
```css
:root {
    --primary-color: #593500;    /* YummyTummy brown */
    --secondary-color: #ffffff;   /* White */
    --accent-color: #f5f2ed;     /* Cream */
    --highlight-color: #ffc107;   /* Yellow */
}
```

#### **Component Styles**
- **Header**: Fixed navigation with mobile responsiveness
- **Product Cards**: Expandable design with hover effects
- **Cart**: Table layout with quantity controls
- **Forms**: Consistent styling with validation states

---

## ⚡ JavaScript Functionality

### **Main JavaScript** (`static/yummytummy_store/js/main.js`)

#### **Cart Button Handling** (Lines 150-280)
```javascript
addToCartButtons.forEach(button => {
    button.addEventListener('click', function(e) {
        // Container detection
        const isProductShowcase = this.closest('.product-showcase') !== null;
        const isExpandableCard = this.closest('.expandable-card') !== null;
        
        // Allow form submission for showcase buttons
        if (isProductShowcase || isExpandableCard) {
            return true; // Submit form immediately
        }
        
        // Animation for other pages
        // ... flying image animation code
    });
});
```

#### **Quantity Selectors** (Lines 98-144)
```javascript
quantitySelectors.forEach(selector => {
    const minusButton = selector.querySelector('.minus');
    const plusButton = selector.querySelector('.plus');
    
    minusButton.addEventListener('click', () => {
        if (value > 1) {
            input.value = value - 1;
            // Auto-submit if in cart
            const updateForm = selector.closest('.update-form');
            if (updateForm) updateForm.submit();
        }
    });
});
```

### **Expandable Cards** (`static/yummytummy_store/js/expandable-cards.js`)

#### **Card Expansion Logic** (Lines 35-84)
```javascript
function expandCard(card, expandBtn, expandedSection) {
    // Close other cards first
    closeOtherExpandedCards(card);
    
    // Expand current card
    card.classList.add('expanded');
    expandedSection.style.display = 'block';
    
    // Smooth scroll if needed
    setTimeout(() => scrollToCardIfNeeded(card), 200);
}
```

---

## 🗄️ Database Schema & Relationships

### **Entity Relationship Diagram**
```
User (Django Auth)
├── Orders (1:N)
│   ├── OrderItems (1:N)
│   │   ├── Product (N:1)
│   │   └── ProductVariant (N:1, optional)
│   ├── Coupon (N:1, optional)
│   └── OrderTrackingStatus (1:N)
├── AutoCreatedAccount (1:1, optional)
└── CouponUsage (1:N)

Category
└── Products (1:N)
    ├── ProductVariants (1:N)
    └── ProductIngredients (N:N via through table)

Coupon
├── Orders (1:N)
└── CouponUsage (1:N)
```

### **Key Indexes** (Performance Optimization)
```python
# Product indexes
models.Index(fields=['id', 'slug']),
models.Index(fields=['name']),
models.Index(fields=['-created']),

# Order indexes  
models.Index(fields=['-created']),

# Coupon indexes
models.Index(fields=['code']),
models.Index(fields=['valid_from', 'valid_to']),
```

---

## 🔗 API Endpoints & Views

### **URL Routing** (`yummytummy_store/urls.py`)

#### **Product URLs**
- `GET /` → `views.home` → Homepage with featured products
- `GET /products/` → `views.product_list` → Product catalog
- `GET /product/<slug>/` → `views.product_detail` → Individual product

#### **Cart URLs**
- `GET /cart/` → `views.cart_detail` → Cart contents
- `POST /cart/add/<int:product_id>/` → `views.cart_add` → Add to cart
- `POST /cart/update/<str:cart_key>/` → `views.cart_update` → Update quantity

#### **Checkout URLs**
- `GET /checkout/` → `views.checkout` → Shipping form
- `POST /checkout/payment/` → `views.payment` → Payment processing
- `GET /checkout/confirmation/` → `views.order_confirmation` → Order success

#### **M-Pesa URLs**
- `POST /mpesa/callback/` → `views.mpesa_callback` → Payment webhook
- `GET /mpesa/test-auth/` → `views.test_mpesa_auth` → Debug endpoint

### **View Functions** (`yummytummy_store/views.py`)

#### **Cart Add View** (Lines 108-169)
```python
@require_POST
def cart_add(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    form = CartAddProductForm(request.POST)
    
    if form.is_valid():
        # Handle variant selection
        selected_variant = cd.get('selected_variant')
        if selected_variant and selected_variant != 'base':
            variant = ProductVariant.objects.get(id=selected_variant, product=product)
            variant_price = product.price + variant.additional_price
        
        # Update session cart
        cart_key = f"{product_id}_variant_{variant.id}" if variant else f"{product_id}_base"
        cart[cart_key] = {
            'product_id': product_id,
            'variant_id': variant.id if variant else None,
            'quantity': cd['quantity'],
            'price': str(variant_price),
            'name': variant_name,
        }
        
        request.session.modified = True
        messages.success(request, f'{variant_name} added to your cart.')
    
    return redirect('yummytummy_store:cart_detail')
```

---

## 🔐 Authentication & Session Management

### **Session-Based Cart** (`yummytummy_store/context_processors.py`)
```python
def cart_processor(request):
    # Ensure cart exists in session
    if 'cart' not in request.session:
        request.session['cart'] = {}
        request.session.modified = True
    
    cart = request.session['cart']
    cart_items_count = sum(int(item.get('quantity', 0)) for item in cart.values())
    
    return {
        'cart': cart,
        'cart_items_count': cart_items_count
    }
```

### **Automatic Account Creation** (`yummytummy_store/services.py:39-61`)
```python
@staticmethod
def create_user_account(order_data):
    email = order_data['email']
    
    # Check if user exists
    existing_user = User.objects.filter(email=email).first()
    if existing_user:
        return existing_user, None
    
    # Generate secure password
    temp_password = OrderTrackingEmailService.generate_secure_password()
    
    # Create new user
    user = User.objects.create_user(
        username=email,
        email=email,
        first_name=order_data['first_name'],
        last_name=order_data['last_name'],
        password=temp_password
    )
    
    return user, temp_password
```

### **First-Time Login Flow** (`yummytummy_store/views.py:759-806`)
```python
def first_time_login(request, token):
    try:
        auto_account = AutoCreatedAccount.objects.get(
            first_login_token=token,
            token_expires__gt=timezone.now()
        )
        
        # Auto-login the user
        login(request, auto_account.user)
        auto_account.first_login_completed = True
        auto_account.save()
        
        return redirect('yummytummy_store:order_tracking_dashboard')
        
    except AutoCreatedAccount.DoesNotExist:
        messages.error(request, "Invalid or expired login link.")
        return redirect('yummytummy_store:home')
```

---

## 💳 Payment Integration (M-Pesa)

### **M-Pesa Service Class** (`yummytummy_store/mpesa_service.py`)

#### **STK Push Initiation** (Lines 98-194)
```python
def initiate_stk_push(self, phone_number, amount, order_id, callback_url):
    # Get access token
    access_token = self.get_access_token()
    
    # Generate password and timestamp
    password, timestamp = self.generate_password()
    
    # Format phone number (254XXXXXXXXX)
    formatted_phone = self.format_phone_number(phone_number)
    
    # Prepare STK Push payload
    payload = {
        'BusinessShortCode': int(self.business_short_code),
        'Password': password,
        'Timestamp': timestamp,
        'TransactionType': 'CustomerPayBillOnline',
        'Amount': int(float(amount)),
        'PartyA': formatted_phone,
        'PartyB': int(self.business_short_code),
        'PhoneNumber': formatted_phone,
        'CallBackURL': callback_url,
        'AccountReference': f'YummyTummy-{order_id}',
        'TransactionDesc': f'Payment for YummyTummy Order #{order_id}'
    }
    
    # Make API request
    response = requests.post(self.stk_push_url, headers=headers, json=payload, timeout=30)
    
    return {
        'success': result.get('ResponseCode') == '0',
        'checkout_request_id': result.get('CheckoutRequestID'),
        'merchant_request_id': result.get('MerchantRequestID')
    }
```

#### **Payment Callback Processing** (`yummytummy_store/views.py:888-976`)
```python
@csrf_exempt
def mpesa_callback(request):
    if request.method == 'POST':
        callback_data = json.loads(request.body.decode('utf-8'))
        stk_callback = callback_data.get('Body', {}).get('stkCallback', {})
        
        checkout_request_id = stk_callback.get('CheckoutRequestID')
        result_code = stk_callback.get('ResultCode')
        
        # Find order by checkout request ID
        order = Order.objects.get(mpesa_checkout_request_id=checkout_request_id)
        
        if result_code == 0:  # Payment successful
            # Extract payment details
            callback_metadata = stk_callback.get('CallbackMetadata', {}).get('Item', [])
            for item in callback_metadata:
                if item.get('Name') == 'MpesaReceiptNumber':
                    receipt_number = item.get('Value')
            
            # Update order
            order.payment_status = 'completed'
            order.transaction_id = receipt_number
            order.save()
            
            # Create tracking status
            OrderTrackingStatus.objects.create(
                order=order,
                status='payment_confirmed',
                message=f'M-Pesa payment confirmed. Receipt: {receipt_number}'
            )
        else:
            # Payment failed
            order.payment_status = 'failed'
            order.save()
    
    return JsonResponse({'ResultCode': 0, 'ResultDesc': 'Success'})
```

---

## 📦 Order Management & Tracking

### **Order Status Progression**
1. **Order Created** → `payment_status='processing'`
2. **Payment Confirmed** → `payment_status='completed'` + tracking status
3. **Order Processing** → Tracking status updates
4. **Shipped** → Tracking status with shipping details
5. **Delivered** → Final tracking status

### **Order Tracking Service** (`yummytummy_store/services.py:170-220`)
```python
class OrderTrackingService:
    @staticmethod
    def create_initial_tracking_status(order):
        OrderTrackingStatus.objects.create(
            order=order,
            status='order_received',
            message='Your order has been received and is being processed.'
        )
    
    @staticmethod
    def get_order_progress_percentage(order):
        status_progression = {
            'order_received': 20,
            'payment_confirmed': 40,
            'processing': 60,
            'shipped': 80,
            'delivered': 100
        }
        
        latest_status = order.get_latest_tracking_status()
        if latest_status:
            return status_progression.get(latest_status.status, 20)
        return 20
```

### **Email Notifications** (`yummytummy_store/services.py:115-168`)
```python
@staticmethod
def send_order_confirmation_with_account(order, user, temp_password, auto_account, request=None):
    # Generate first-time login URL
    login_url = OrderTrackingEmailService.get_first_login_url(auto_account, request)
    
    context = {
        'order': order,
        'user': user,
        'temp_password': temp_password,
        'login_url': login_url,
        'order_items': order_items,
        'token_expires_days': 7,
    }
    
    # Send HTML email
    html_message = render_to_string('yummytummy_store/emails/order_confirmation_with_account.html', context)
    
    send_mail(
        subject=f'YummyTummy Order #{order.get_order_number()} - Account Created',
        message=strip_tags(html_message),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        html_message=html_message,
    )
```

---

## 🔧 Current Status & Recent Fixes

### **✅ Recently Fixed Issues**
1. **Cart Buttons on Homepage** - JavaScript now properly recognizes `.product-showcase` and `.expandable-card` containers
2. **Variant Selection** - Form submissions work correctly for both base products and variants
3. **Animation Conflicts** - Showcase buttons submit immediately without animation delays

### **✅ Verified Working Features**
- ✅ Product browsing and variant selection
- ✅ Cart operations (add, update, remove)
- ✅ Checkout process with automatic account creation
- ✅ M-Pesa payment integration
- ✅ Order tracking and email notifications
- ✅ Admin interface for content management

### **📋 Performance Considerations**
- Session-based cart storage (documented in `PERFORMANCE_ISSUES_TRACKER.md`)
- Database query optimization needed for cart operations
- M-Pesa API calls could benefit from async processing
- Image optimization through Uploadcare CDN

---

**Documentation Maintained By**: YummyTummy Development Team  
**Next Review**: Quarterly or after major feature updates
