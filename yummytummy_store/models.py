from django.db import models
from django.urls import reverse
from django.utils.text import slugify
from django.utils import timezone
from django.contrib.auth.models import User
from pyuploadcare.dj.models import ImageField
import secrets

class Category(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    slug = models.SlugField(max_length=100, unique=True)

    class Meta:
        verbose_name_plural = 'Categories'
        ordering = ['name']

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('yummytummy_store:product_list_by_category', args=[self.slug])

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class Ingredient(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name


class Product(models.Model):
    FEATURE_TYPE_CHOICES = [
        ('bestseller', 'Bestseller'),
        ('seasonal', 'Seasonal'),
        ('limited_time', 'Limited Time'),
        ('new', 'New Arrival'),
        ('sale', 'On Sale'),
    ]

    CURRENCY = 'KES'  # Kenyan Shillings as default currency

    category = models.ForeignKey(Category, related_name='products', on_delete=models.CASCADE)
    name = models.CharField(max_length=200)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2, help_text="Price in Kenyan Shillings (KES)")
    size = models.CharField(max_length=50, blank=True)
    image = ImageField(blank=True, manual_crop="", help_text="Upload product image")
    legacy_image = models.ImageField(upload_to='products/%Y/%m/%d', blank=True, null=True, editable=False)
    slug = models.SlugField(max_length=200, unique=True)
    is_available = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)
    feature_type = models.CharField(max_length=20, choices=FEATURE_TYPE_CHOICES, blank=True)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    def get_formatted_price(self):
        """Return the price formatted with KES currency symbol and thousands separator"""
        return f"KSh {self.price:,.2f}"

    def get_image_url(self):
        """Return the image URL, handling both Uploadcare and legacy images"""
        try:
            if self.image:
                return self.image.cdn_url
        except (AttributeError, ValueError):
            # Handle cases where Uploadcare image might be corrupted or invalid
            pass

        if self.legacy_image:
            try:
                return self.legacy_image.url
            except (AttributeError, ValueError):
                pass

        return None

    class Meta:
        ordering = ['name']
        indexes = [
            models.Index(fields=['id', 'slug']),
            models.Index(fields=['name']),
            models.Index(fields=['-created']),
        ]

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('yummytummy_store:product_detail', args=[self.slug])

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)

        # If this is a new product with a legacy image but no Uploadcare image,
        # we'll keep the legacy image for backward compatibility
        # In the future, when updating the product, the admin can upload a new image via Uploadcare

        super().save(*args, **kwargs)


class ProductVariant(models.Model):
    product = models.ForeignKey(Product, related_name='variants', on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    additional_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    def __str__(self):
        return f"{self.product.name} - {self.name}"

    @property
    def calculated_price(self):
        """Calculate the total price for this variant (base price + additional price)"""
        return self.product.price + self.additional_price

    def get_formatted_price(self):
        """Return the calculated price formatted with KES currency symbol and thousands separator"""
        return f"KSh {self.calculated_price:,.2f}"


class ProductIngredient(models.Model):
    product = models.ForeignKey(Product, related_name='ingredients', on_delete=models.CASCADE)
    ingredient = models.ForeignKey(Ingredient, related_name='products', on_delete=models.CASCADE)
    percentage = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)

    def __str__(self):
        return f"{self.product.name} - {self.ingredient.name} ({self.percentage}%)"


class Order(models.Model):
    PAYMENT_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
    ]

    PAYMENT_METHOD_CHOICES = [
        ('mpesa', 'M-Pesa'),
        ('card', 'Credit/Debit Card'),
        ('bank', 'Bank Transfer'),
    ]

    # Customer Information
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                           related_name='orders', help_text="User account (if account exists)")
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.CharField(max_length=20)

    # Shipping Address
    address = models.CharField(max_length=250)
    area = models.CharField(max_length=100, blank=True, help_text="Area/Neighborhood")
    estate = models.CharField(max_length=100, blank=True, help_text="Estate/Community name")
    building = models.CharField(max_length=100, blank=True, help_text="Apartment/Building/House number")
    landmark = models.CharField(max_length=150, blank=True, help_text="Nearby recognizable location")
    # Making these fields optional but not removing them to maintain backward compatibility
    postal_code = models.CharField(max_length=20, blank=True, null=True)
    city = models.CharField(max_length=100, blank=True, null=True)
    county = models.CharField(max_length=100, blank=True, null=True)

    # Order Tracking Fields
    auto_created_account = models.BooleanField(default=False,
                                             help_text="Whether an account was automatically created for this order")
    account_creation_email_sent = models.BooleanField(default=False,
                                                    help_text="Whether the account creation email was sent")

    # Timestamps
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    # Payment Information
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='pending')
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES, default='mpesa')
    mpesa_phone = models.CharField(max_length=20, blank=True)
    transaction_id = models.CharField(max_length=100, blank=True)

    # M-Pesa specific fields
    mpesa_checkout_request_id = models.CharField(max_length=100, blank=True, help_text="M-Pesa STK Push Checkout Request ID")
    mpesa_merchant_request_id = models.CharField(max_length=100, blank=True, help_text="M-Pesa Merchant Request ID")
    mpesa_receipt_number = models.CharField(max_length=100, blank=True, help_text="M-Pesa Receipt Number")
    mpesa_transaction_date = models.DateTimeField(null=True, blank=True, help_text="M-Pesa Transaction Date")

    order_notes = models.TextField(blank=True)

    # Pricing
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, help_text="Total amount in Kenyan Shillings (KES)")
    coupon = models.ForeignKey('Coupon', related_name='orders', on_delete=models.SET_NULL, null=True, blank=True)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text="Discount amount in Kenyan Shillings (KES)")
    subtotal_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text="Subtotal amount in Kenyan Shillings (KES)")

    class Meta:
        ordering = ['-created']
        indexes = [
            models.Index(fields=['-created']),
        ]

    def __str__(self):
        return f'Order {self.id}'

    def get_total_cost(self):
        return sum(item.get_cost() for item in self.items.all())

    def get_subtotal(self):
        """Get subtotal before discount"""
        return self.get_total_cost()

    def get_total_after_discount(self):
        """Get total after applying discount"""
        return self.get_subtotal() - self.discount_amount

    def get_order_number(self):
        return f'MSL-{self.id:06d}'

    def get_formatted_total(self):
        """Return the total amount formatted with KES currency symbol and thousands separator"""
        return f"KSh {self.total_amount:,.2f}"

    def get_formatted_subtotal(self):
        """Return the subtotal amount formatted with KES currency symbol and thousands separator"""
        return f"KSh {self.subtotal_amount:,.2f}"

    def get_formatted_discount(self):
        """Return the discount amount formatted with KES currency symbol and thousands separator"""
        return f"KSh {self.discount_amount:,.2f}"

    def get_customer_name(self):
        """Get the full customer name"""
        return f"{self.first_name} {self.last_name}"

    def get_latest_tracking_status(self):
        """Get the most recent tracking status for this order"""
        return self.tracking_statuses.first()

    def get_current_status_display(self):
        """Get the current status display text"""
        latest_status = self.get_latest_tracking_status()
        if latest_status:
            return latest_status.get_status_display()
        return self.get_payment_status_display()

    def has_account(self):
        """Check if this order is associated with a user account"""
        return self.user is not None

    def is_guest_order(self):
        """Check if this is a guest order (no associated user account)"""
        return self.user is None

    def save(self, *args, **kwargs):
        # Calculate subtotal if not already set
        if self.subtotal_amount == 0:
            self.subtotal_amount = self.get_subtotal()

        # Ensure total amount reflects any discount
        if self.discount_amount > 0:
            self.total_amount = self.subtotal_amount - self.discount_amount

        super().save(*args, **kwargs)


class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name='items', on_delete=models.CASCADE)
    product = models.ForeignKey(Product, related_name='order_items', on_delete=models.CASCADE)
    variant = models.ForeignKey(ProductVariant, related_name='order_items', on_delete=models.CASCADE, null=True, blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, help_text="Price in Kenyan Shillings (KES)")
    quantity = models.PositiveIntegerField(default=1)

    def __str__(self):
        return f'{self.quantity}x {self.product.name}'

    def get_cost(self):
        return self.price * self.quantity

    def get_formatted_price(self):
        """Return the price formatted with KES currency symbol and thousands separator"""
        return f"KSh {self.price:,.2f}"

    def get_formatted_cost(self):
        """Return the total cost formatted with KES currency symbol and thousands separator"""
        return f"KSh {self.get_cost():,.2f}"


class Coupon(models.Model):
    DISCOUNT_TYPE_CHOICES = [
        ('percentage', 'Percentage'),
        ('fixed', 'Fixed Amount'),
    ]

    code = models.CharField(max_length=50, unique=True)
    discount_type = models.CharField(max_length=10, choices=DISCOUNT_TYPE_CHOICES, default='percentage')
    discount_value = models.DecimalField(max_digits=10, decimal_places=2,
                                        help_text="For percentage type: enter percentage value (e.g., 10 for 10%). "
                                                 "For fixed amount type: enter amount in Kenyan Shillings (KES)")
    valid_from = models.DateTimeField()
    valid_to = models.DateTimeField()
    min_order_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0,
                                          help_text="Minimum order amount in Kenyan Shillings (KES)")
    is_active = models.BooleanField(default=True)
    usage_limit = models.PositiveIntegerField(default=1, help_text="Maximum number of times this coupon can be used")
    usage_count = models.PositiveIntegerField(default=0, help_text="Number of times this coupon has been used")
    per_customer_limit = models.PositiveIntegerField(default=1, help_text="Maximum number of times a customer can use this coupon")
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created']
        indexes = [
            models.Index(fields=['code']),
            models.Index(fields=['valid_from', 'valid_to']),
            models.Index(fields=['is_active']),
        ]

    def __str__(self):
        return self.code

    def is_valid(self, order_total=None, user=None):
        """Check if the coupon is valid for the given order total and user"""
        from django.utils import timezone
        now = timezone.now()

        # Check if coupon is active and within valid date range
        if not self.is_active or now < self.valid_from or now > self.valid_to:
            return False

        # Check if coupon has reached its usage limit
        if self.usage_count >= self.usage_limit:
            return False

        # Check if order meets minimum amount requirement
        if order_total and order_total < self.min_order_amount:
            return False

        # Check if user has reached per-customer limit
        if user and not user.is_anonymous:
            user_usage_count = CouponUsage.objects.filter(coupon=self, user=user).count()
            if user_usage_count >= self.per_customer_limit:
                return False

        return True

    def calculate_discount(self, order_total):
        """Calculate the discount amount based on the coupon type and value"""
        if self.discount_type == 'percentage':
            # Percentage discount
            discount = order_total * (self.discount_value / 100)
        else:
            # Fixed amount discount
            discount = min(self.discount_value, order_total)  # Don't exceed order total

        return discount

    def get_formatted_discount_value(self):
        """Return the discount value formatted appropriately based on type"""
        if self.discount_type == 'percentage':
            return f"{self.discount_value:.0f}%"
        else:
            return f"KSh {self.discount_value:,.2f}"

    def get_formatted_min_order_amount(self):
        """Return the minimum order amount formatted with KES currency symbol and thousands separator"""
        return f"KSh {self.min_order_amount:,.2f}"

    def clean(self):
        from django.core.exceptions import ValidationError

        # Convert code to uppercase for validation
        if self.code:
            self.code = self.code.upper()

            # Check if a coupon with this code already exists (excluding self if updating)
            existing_coupon = Coupon.objects.filter(code=self.code)
            if self.pk:  # If this is an existing coupon being updated
                existing_coupon = existing_coupon.exclude(pk=self.pk)

            if existing_coupon.exists():
                raise ValidationError({
                    'code': f'A coupon with code "{self.code}" already exists. Please use a different code.'
                })

        super().clean()

    def save(self, *args, **kwargs):
        # Convert code to uppercase for consistency
        if self.code:
            self.code = self.code.upper()
        super().save(*args, **kwargs)


class CouponUsage(models.Model):
    coupon = models.ForeignKey(Coupon, related_name='usages', on_delete=models.CASCADE)
    user = models.ForeignKey('auth.User', related_name='coupon_usages', on_delete=models.CASCADE, null=True, blank=True)
    order = models.ForeignKey(Order, related_name='coupon_usages', on_delete=models.CASCADE)
    used_at = models.DateTimeField(auto_now_add=True)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, help_text="Discount amount in Kenyan Shillings (KES)")

    class Meta:
        unique_together = ('coupon', 'order')
        ordering = ['-used_at']

    def __str__(self):
        return f'{self.coupon.code} used on Order {self.order.id}'

    def get_formatted_discount_amount(self):
        """Return the discount amount formatted with KES currency symbol and thousands separator"""
        return f"KSh {self.discount_amount:,.2f}"


# Order Tracking Models for Automatic Account Creation

class AutoCreatedAccount(models.Model):
    """
    Model to track accounts that were automatically created during checkout.
    This helps manage the order tracking system and first-time login process.
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='auto_created_account')
    created_during_order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='auto_account_record')
    initial_password_sent = models.BooleanField(default=False, help_text="Whether the initial password email was sent")
    first_login_token = models.CharField(max_length=64, unique=True, null=True, blank=True,
                                       help_text="Token for first-time login from email")
    token_expires = models.DateTimeField(null=True, blank=True, help_text="When the first-login token expires")
    first_login_completed = models.BooleanField(default=False, help_text="Whether user has completed first login")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['first_login_token']),
            models.Index(fields=['token_expires']),
            models.Index(fields=['-created_at']),
        ]

    def __str__(self):
        return f'Auto-created account for {self.user.email} (Order {self.created_during_order.id})'

    def generate_first_login_token(self):
        """Generate a secure token for first-time login"""
        self.first_login_token = secrets.token_urlsafe(32)
        self.token_expires = timezone.now() + timezone.timedelta(days=7)  # Token valid for 7 days
        self.save()
        return self.first_login_token

    def is_token_valid(self):
        """Check if the first-login token is still valid"""
        if not self.first_login_token or not self.token_expires:
            return False
        return timezone.now() < self.token_expires

    def mark_first_login_completed(self):
        """Mark that the user has completed their first login"""
        self.first_login_completed = True
        self.first_login_token = None  # Clear the token after use
        self.token_expires = None
        self.save()


class OrderTrackingStatus(models.Model):
    """
    Model to track order status updates for the order tracking system.
    This provides detailed status information beyond the basic payment status.
    """
    STATUS_CHOICES = [
        ('order_received', 'Order Received'),
        ('payment_confirmed', 'Payment Confirmed'),
        ('processing', 'Processing'),
        ('packaging', 'Packaging'),
        ('shipped', 'Shipped'),
        ('out_for_delivery', 'Out for Delivery'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
        ('refunded', 'Refunded'),
    ]

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='tracking_statuses')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    message = models.TextField(blank=True, help_text="Additional details about this status update")
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                                 help_text="Admin user who created this status update")

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['order', '-created_at']),
            models.Index(fields=['status']),
        ]
        verbose_name_plural = 'Order Tracking Statuses'

    def __str__(self):
        return f'Order {self.order.id} - {self.get_status_display()}'

    def get_status_icon(self):
        """Return appropriate icon class for the status"""
        status_icons = {
            'order_received': 'fas fa-check-circle',
            'payment_confirmed': 'fas fa-credit-card',
            'processing': 'fas fa-cogs',
            'packaging': 'fas fa-box',
            'shipped': 'fas fa-truck',
            'out_for_delivery': 'fas fa-shipping-fast',
            'delivered': 'fas fa-home',
            'cancelled': 'fas fa-times-circle',
            'refunded': 'fas fa-undo',
        }
        return status_icons.get(self.status, 'fas fa-info-circle')

    def get_status_color(self):
        """Return appropriate color class for the status"""
        status_colors = {
            'order_received': 'text-info',
            'payment_confirmed': 'text-success',
            'processing': 'text-warning',
            'packaging': 'text-warning',
            'shipped': 'text-primary',
            'out_for_delivery': 'text-primary',
            'delivered': 'text-success',
            'cancelled': 'text-danger',
            'refunded': 'text-secondary',
        }
        return status_colors.get(self.status, 'text-muted')
