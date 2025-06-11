from django.contrib import admin
from django.utils.html import format_html
from pyuploadcare.dj.forms import FileWidget
from pyuploadcare.dj.models import ImageField
from .models import (
    Category, Product, ProductVariant, Ingredient, ProductIngredient,
    Order, OrderItem, Coupon, CouponUsage
)

class ProductVariantInline(admin.TabularInline):
    model = ProductVariant
    extra = 1

class ProductIngredientInline(admin.TabularInline):
    model = ProductIngredient
    extra = 1

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug']
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ['name']

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'formatted_price', 'product_image', 'is_available', 'is_featured', 'feature_type', 'created', 'updated']
    list_filter = ['is_available', 'is_featured', 'feature_type', 'created', 'updated', 'category']
    list_editable = ['is_available', 'is_featured', 'feature_type']
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ['name', 'description']
    date_hierarchy = 'created'
    inlines = [ProductVariantInline, ProductIngredientInline]

    # Use Uploadcare widget for the image field
    formfield_overrides = {
        ImageField: {'widget': FileWidget(attrs={
            'data-images-only': 'true',
            'data-preview-step': 'true',
            'data-image-shrink': '1024x1024',
            'data-crop': 'free',
            'data-validators': 'image, max-size: 10485760'
        })},
    }

    def formatted_price(self, obj):
        # Pre-format the value first, then pass it to format_html
        formatted_value = 'KSh {:,.2f}'.format(obj.price)
        return format_html('<span>{}</span>', formatted_value)
    formatted_price.short_description = 'Price (KES)'

    def product_image(self, obj):
        """Display product image thumbnail in admin list view"""
        try:
            if obj.image:
                return format_html('<img src="{}/-/preview/100x100/" width="50" height="50" style="object-fit: cover;" />',
                                  obj.image.cdn_url)
        except (AttributeError, ValueError):
            pass

        try:
            if obj.legacy_image:
                return format_html('<img src="{}" width="50" height="50" style="object-fit: cover;" />',
                                  obj.legacy_image.url)
        except (AttributeError, ValueError):
            pass

        return format_html('<span style="color: #999;">No image</span>')
    product_image.short_description = 'Image'

    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'category', 'description', 'slug')
        }),
        ('Pricing and Size', {
            'fields': ('price', 'size'),
            'description': 'Enter price in Kenyan Shillings (KES)'
        }),
        ('Images', {
            'fields': ('image',),
            'description': 'Upload product images using Uploadcare. Images will be optimized automatically.'
        }),
        ('Status', {
            'fields': ('is_available', 'is_featured', 'feature_type')
        }),
    )

    actions = ['make_available', 'make_unavailable', 'make_featured', 'make_unfeatured']

    @admin.action(description='Mark selected products as available')
    def make_available(self, request, queryset):
        queryset.update(is_available=True)

    @admin.action(description='Mark selected products as unavailable')
    def make_unavailable(self, request, queryset):
        queryset.update(is_available=False)

    @admin.action(description='Mark selected products as featured')
    def make_featured(self, request, queryset):
        queryset.update(is_featured=True)

    @admin.action(description='Remove featured status from selected products')
    def make_unfeatured(self, request, queryset):
        queryset.update(is_featured=False)

@admin.register(Ingredient)
class IngredientAdmin(admin.ModelAdmin):
    list_display = ['name']
    search_fields = ['name', 'description']


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    raw_id_fields = ['product']
    extra = 0


class OrderCouponUsageInline(admin.TabularInline):
    model = CouponUsage
    extra = 0
    readonly_fields = ['coupon', 'user', 'used_at', 'discount_amount']
    can_delete = False
    max_num = 0  # Don't allow adding new usages via admin


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['id', 'get_order_number', 'first_name', 'last_name', 'email',
                    'payment_status', 'payment_method', 'formatted_subtotal', 'formatted_discount', 'formatted_total', 'created']
    list_filter = ['payment_status', 'payment_method', 'created', 'updated']
    search_fields = ['first_name', 'last_name', 'email', 'transaction_id']
    date_hierarchy = 'created'
    inlines = [OrderItemInline, OrderCouponUsageInline]
    readonly_fields = ['get_order_number', 'subtotal_amount', 'discount_amount', 'formatted_subtotal', 'formatted_discount', 'formatted_total']
    fieldsets = (
        ('Customer Information', {
            'fields': (('first_name', 'last_name'), ('email', 'phone'))
        }),
        ('Delivery Address', {
            'fields': ('address', 'area', 'estate', 'building', 'landmark')
        }),
        ('Order Details', {
            'fields': (('payment_status', 'payment_method'), 'mpesa_phone', 'transaction_id',
                      ('formatted_subtotal', 'formatted_discount', 'formatted_total'), 'coupon', 'order_notes'),
            'description': 'All monetary values are in Kenyan Shillings (KES)'
        }),
    )

    def formatted_subtotal(self, obj):
        # Pre-format the value first, then pass it to format_html
        formatted_value = 'KSh {:,.2f}'.format(obj.subtotal_amount)
        return format_html('<span>{}</span>', formatted_value)
    formatted_subtotal.short_description = 'Subtotal (KES)'

    def formatted_discount(self, obj):
        # Pre-format the value first, then pass it to format_html
        formatted_value = 'KSh {:,.2f}'.format(obj.discount_amount)
        return format_html('<span>{}</span>', formatted_value)
    formatted_discount.short_description = 'Discount (KES)'

    def formatted_total(self, obj):
        # Pre-format the value first, then pass it to format_html
        formatted_value = 'KSh {:,.2f}'.format(obj.total_amount)
        return format_html('<span><strong>{}</strong></span>', formatted_value)
    formatted_total.short_description = 'Total (KES)'


class CouponUsageInline(admin.TabularInline):
    model = CouponUsage
    extra = 0
    readonly_fields = ['order', 'user', 'used_at', 'discount_amount']
    can_delete = False
    max_num = 0  # Don't allow adding new usages via admin


@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = ['code', 'discount_display', 'valid_from', 'valid_to', 'is_active',
                   'usage_count', 'usage_limit', 'formatted_min_order_amount', 'created']
    list_filter = ['is_active', 'discount_type', 'created', 'valid_from', 'valid_to']
    search_fields = ['code']
    readonly_fields = ['usage_count', 'created', 'updated', 'existing_codes']
    inlines = [CouponUsageInline]
    fieldsets = (
        ('Coupon Information', {
            'fields': ('existing_codes', 'code', ('discount_type', 'discount_value'), ('valid_from', 'valid_to'), 'is_active'),
            'description': 'For fixed amount discounts, enter value in Kenyan Shillings (KES)'
        }),
        ('Usage Limits', {
            'fields': ('min_order_amount', ('usage_limit', 'usage_count'), 'per_customer_limit'),
            'description': 'Minimum order amount is in Kenyan Shillings (KES)'
        }),
        ('Metadata', {
            'fields': ('created', 'updated'),
            'classes': ('collapse',)
        }),
    )

    def discount_display(self, obj):
        if obj.discount_type == 'percentage':
            # Format percentage with no decimal places
            formatted_value = '{:.0f}%'.format(obj.discount_value)
            return format_html('<span style="color: #28a745;">{}</span>', formatted_value)
        else:
            # Format currency with 2 decimal places and KES symbol
            formatted_value = 'KSh {:,.2f}'.format(obj.discount_value)
            return format_html('<span style="color: #007bff;">{}</span>', formatted_value)
    discount_display.short_description = 'Discount'

    def formatted_min_order_amount(self, obj):
        # Pre-format the value first, then pass it to format_html
        formatted_value = 'KSh {:,.2f}'.format(obj.min_order_amount)
        return format_html('<span>{}</span>', formatted_value)
    formatted_min_order_amount.short_description = 'Min. Order (KES)'

    def existing_codes(self, obj):
        """Display existing coupon codes to help admin avoid duplicates"""
        from django.utils.safestring import mark_safe

        codes = Coupon.objects.exclude(pk=obj.pk if obj else None).values_list('code', flat=True)
        if not codes:
            return mark_safe('<em>No existing coupon codes.</em>')

        code_list = ''.join([f'<li><code>{code}</code></li>' for code in codes])
        return mark_safe(f'''
            <div style="margin-bottom: 10px;">
                <strong>Existing coupon codes:</strong>
                <ul style="max-height: 100px; overflow-y: auto; border: 1px solid #ddd; padding: 10px; background: #f9f9f9;">
                    {code_list}
                </ul>
                <p style="color: #666; font-size: 12px;">
                    Note: Coupon codes must be unique. All codes are automatically converted to uppercase.
                </p>
            </div>
        ''')
    existing_codes.short_description = 'Existing Coupon Codes'

    def get_readonly_fields(self, request, obj=None):
        readonly_fields = list(self.readonly_fields)
        if obj:  # Editing an existing object
            readonly_fields.append('code')  # Make code field readonly when editing
        return readonly_fields

    def save_model(self, request, obj, form, change):
        try:
            super().save_model(request, obj, form, change)
        except Exception as e:
            # If there's an error saving the model, add a more user-friendly message
            if 'UNIQUE constraint failed' in str(e) and 'code' in str(e):
                from django.contrib import messages
                messages.error(request, f'Error: The coupon code "{obj.code}" already exists. Please use a different code.')
                # Re-raise the exception to prevent saving
                raise
            # Re-raise other exceptions
            raise

    actions = ['activate_coupons', 'deactivate_coupons']

    @admin.action(description='Activate selected coupons')
    def activate_coupons(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} coupons have been activated.')

    @admin.action(description='Deactivate selected coupons')
    def deactivate_coupons(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} coupons have been deactivated.')


@admin.register(CouponUsage)
class CouponUsageAdmin(admin.ModelAdmin):
    list_display = ['coupon_code', 'order_number', 'user_email', 'formatted_discount', 'used_at']
    list_filter = ['used_at', 'coupon']
    search_fields = ['coupon__code', 'order__email', 'user__email']
    readonly_fields = ['coupon', 'order', 'user', 'discount_amount', 'formatted_discount', 'used_at']

    def formatted_discount(self, obj):
        # Pre-format the value first, then pass it to format_html
        formatted_value = 'KSh {:,.2f}'.format(obj.discount_amount)
        return format_html('<span>{}</span>', formatted_value)
    formatted_discount.short_description = 'Discount Amount (KES)'

    def coupon_code(self, obj):
        return obj.coupon.code
    coupon_code.short_description = 'Coupon Code'

    def order_number(self, obj):
        return obj.order.get_order_number()
    order_number.short_description = 'Order Number'

    def user_email(self, obj):
        if obj.user:
            return obj.user.email
        return obj.order.email
    user_email.short_description = 'User Email'

    def has_add_permission(self, request):
        return False  # Prevent adding coupon usages directly


# Admin site customization with Maslove branding
admin.site.site_header = 'Maslove Administration'
admin.site.site_title = 'Maslove Admin'
admin.site.index_title = 'Maslove Management'
