from django.contrib import admin
from django.utils.html import format_html
from pyuploadcare.dj.forms import FileWidget
from pyuploadcare.dj.models import ImageField
from .models import (
    Category, Product, ProductVariant, Ingredient, ProductIngredient,
    Order, OrderItem, Coupon, CouponUsage, OrderTrackingStatus,
    RecipeCategory, Recipe, RecipePurchase
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


class OrderTrackingStatusInline(admin.TabularInline):
    model = OrderTrackingStatus
    extra = 1
    readonly_fields = ['created_at', 'created_by']
    fields = ['status', 'message', 'created_by', 'created_at']
    ordering = ['-created_at']

    def save_model(self, request, obj, form, change):
        # Set the created_by field to current user if not set
        if not obj.created_by:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)

        # Send email notification for inline status updates
        try:
            from .services import OrderTrackingEmailService
            OrderTrackingEmailService.send_status_update_email(obj.order, obj)
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to send email notification from inline: {str(e)}")

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('created_by')

    def save_model(self, request, obj, form, change):
        # Set the created_by field to current user if not set
        if not obj.created_by:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('created_by')


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['id', 'get_order_number', 'first_name', 'last_name', 'email',
                    'payment_status', 'payment_method', 'formatted_subtotal', 'formatted_discount', 'formatted_total', 'created']
    list_filter = ['payment_status', 'payment_method', 'created', 'updated']
    search_fields = ['first_name', 'last_name', 'email', 'transaction_id', 'mpesa_receipt_number']
    date_hierarchy = 'created'
    inlines = [OrderItemInline, OrderCouponUsageInline, OrderTrackingStatusInline]
    readonly_fields = ['get_order_number', 'subtotal_amount', 'discount_amount', 'formatted_subtotal', 'formatted_discount', 'formatted_total',
                      'mpesa_checkout_request_id', 'mpesa_merchant_request_id', 'mpesa_receipt_number', 'mpesa_transaction_date']
    fieldsets = (
        ('Customer Information', {
            'fields': (('first_name', 'last_name'), ('email', 'phone'))
        }),
        ('Delivery Address', {
            'fields': ('address', 'area', 'estate', 'building', 'landmark')
        }),
        ('Payment Information', {
            'fields': (('payment_status', 'payment_method'), 'mpesa_phone', 'transaction_id'),
            'description': 'Payment method and status information'
        }),
        ('M-Pesa Details', {
            'fields': ('mpesa_checkout_request_id', 'mpesa_merchant_request_id',
                      'mpesa_receipt_number', 'mpesa_transaction_date'),
            'description': 'M-Pesa transaction details (automatically populated)',
            'classes': ('collapse',)
        }),
        ('Order Totals', {
            'fields': (('formatted_subtotal', 'formatted_discount', 'formatted_total'), 'coupon', 'order_notes'),
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
        # Handle None values safely
        if obj.total_amount is not None:
            formatted_value = 'KSh {:,.2f}'.format(obj.total_amount)
            return format_html('<span><strong>{}</strong></span>', formatted_value)
        return format_html('<span><em>Not calculated</em></span>')
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

    def user_email(self, obj):
        return obj.user.email if obj.user else 'Guest'
    user_email.short_description = 'User Email'

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


@admin.register(OrderTrackingStatus)
class OrderTrackingStatusAdmin(admin.ModelAdmin):
    list_display = ['order_number', 'status', 'message_preview', 'created_at', 'created_by']
    list_filter = ['status', 'created_at']
    search_fields = ['order__id', 'order__first_name', 'order__last_name', 'order__email']
    readonly_fields = ['created_at']
    ordering = ['-created_at']

    fieldsets = (
        ('Order Information', {
            'fields': ('order',)
        }),
        ('Status Update', {
            'fields': ('status', 'message', 'created_by')
        }),
        ('Timestamps', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('order', 'created_by')

    def order_number(self, obj):
        return obj.order.get_order_number()
    order_number.short_description = 'Order #'

    def message_preview(self, obj):
        return obj.message[:50] + '...' if len(obj.message) > 50 else obj.message
    message_preview.short_description = 'Message'

    def save_model(self, request, obj, form, change):
        # Set the created_by field to current user if not set
        if not obj.created_by:
            obj.created_by = request.user

        # Save the object first
        super().save_model(request, obj, form, change)

        # Send email notification to customer for both new and updated status
        try:
            from .services import OrderTrackingEmailService
            OrderTrackingEmailService.send_status_update_email(obj.order, obj)

            if change:
                self.message_user(request, "Status updated and customer notification email sent.", level='success')
            else:
                self.message_user(request, "Status created and customer notification email sent.", level='success')

        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to send email notification: {str(e)}")

            if change:
                self.message_user(request, f"Status updated but email notification failed: {str(e)}", level='warning')
            else:
                self.message_user(request, f"Status created but email notification failed: {str(e)}", level='warning')

    actions = ['mark_as_processing', 'mark_as_packaging', 'mark_as_shipped', 'mark_as_delivered']

    @admin.action(description='Create Processing status for selected orders')
    def mark_as_processing(self, request, queryset):
        count = 0
        email_count = 0
        for tracking_status in queryset:
            new_status = OrderTrackingStatus.objects.create(
                order=tracking_status.order,
                status='processing',
                message='Your order is being processed and prepared for shipment.',
                created_by=request.user
            )
            count += 1

            # Send email notification
            try:
                from .services import OrderTrackingEmailService
                OrderTrackingEmailService.send_status_update_email(new_status.order, new_status)
                email_count += 1
            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Failed to send email for order {new_status.order.id}: {str(e)}")

        self.message_user(request, f"Created Processing status for {count} orders. Sent {email_count} email notifications.")

    @admin.action(description='Create Packaging status for selected orders')
    def mark_as_packaging(self, request, queryset):
        count = 0
        email_count = 0
        for tracking_status in queryset:
            new_status = OrderTrackingStatus.objects.create(
                order=tracking_status.order,
                status='packaging',
                message='Your order is being packaged for shipment.',
                created_by=request.user
            )
            count += 1

            # Send email notification
            try:
                from .services import OrderTrackingEmailService
                OrderTrackingEmailService.send_status_update_email(new_status.order, new_status)
                email_count += 1
            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Failed to send email for order {new_status.order.id}: {str(e)}")

        self.message_user(request, f"Created Packaging status for {count} orders. Sent {email_count} email notifications.")

    @admin.action(description='Create Shipped status for selected orders')
    def mark_as_shipped(self, request, queryset):
        count = 0
        email_count = 0
        for tracking_status in queryset:
            new_status = OrderTrackingStatus.objects.create(
                order=tracking_status.order,
                status='shipped',
                message='Your order has been shipped and is on its way to you.',
                created_by=request.user
            )
            count += 1

            # Send email notification
            try:
                from .services import OrderTrackingEmailService
                OrderTrackingEmailService.send_status_update_email(new_status.order, new_status)
                email_count += 1
            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Failed to send email for order {new_status.order.id}: {str(e)}")

        self.message_user(request, f"Created Shipped status for {count} orders. Sent {email_count} email notifications.")

    @admin.action(description='Create Delivered status for selected orders')
    def mark_as_delivered(self, request, queryset):
        count = 0
        email_count = 0
        for tracking_status in queryset:
            new_status = OrderTrackingStatus.objects.create(
                order=tracking_status.order,
                status='delivered',
                message='Your order has been successfully delivered. Thank you for choosing YummyTummy!',
                created_by=request.user
            )
            count += 1

            # Send email notification
            try:
                from .services import OrderTrackingEmailService
                OrderTrackingEmailService.send_status_update_email(new_status.order, new_status)
                email_count += 1
            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Failed to send email for order {new_status.order.id}: {str(e)}")

        self.message_user(request, f"Created Delivered status for {count} orders. Sent {email_count} email notifications.")

    def has_add_permission(self, request):
        return True  # Allow adding tracking status entries


# ================================================================
# RECIPE ADMINISTRATION
# ================================================================

@admin.register(RecipeCategory)
class RecipeCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'recipe_count', 'created']
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ['name', 'description']
    date_hierarchy = 'created'

    def recipe_count(self, obj):
        count = obj.recipes.count()
        return format_html('<span style="color: #007bff; font-weight: bold;">{}</span>', count)
    recipe_count.short_description = 'Recipes'


@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    list_display = ['title', 'category', 'formatted_price', 'recipe_image', 'difficulty',
                   'total_time_display', 'servings', 'is_published', 'is_featured', 'created']
    list_filter = ['category', 'difficulty', 'is_published', 'is_featured', 'created']
    list_editable = ['is_published', 'is_featured']
    prepopulated_fields = {'slug': ('title',)}
    search_fields = ['title', 'description', 'tags']
    date_hierarchy = 'created'
    filter_horizontal = ['related_products']

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

    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'slug', 'category', 'description')
        }),
        ('Recipe Details', {
            'fields': ('ingredients', 'instructions', 'preview_content'),
            'description': 'Use JSON format for ingredients and instructions. Example: ["1 cup peanuts", "2 tbsp oil"]'
        }),
        ('Timing & Difficulty', {
            'fields': (('prep_time_minutes', 'cook_time_minutes'), ('servings', 'difficulty'))
        }),
        ('Media & Pricing', {
            'fields': ('image', 'price', 'pdf_file'),
            'description': 'Upload recipe image and PDF file. Price is in Kenyan Shillings (KES)'
        }),
        ('Related Products & Tags', {
            'fields': ('related_products', 'tags'),
            'description': 'Select related YummyTummy products for upselling. Tags should be comma-separated.'
        }),
        ('Publishing', {
            'fields': ('is_published', 'is_featured')
        }),
    )

    def formatted_price(self, obj):
        formatted_value = 'KSh {:,.2f}'.format(obj.price)
        return format_html('<span style="color: #28a745; font-weight: bold;">{}</span>', formatted_value)
    formatted_price.short_description = 'Price (KES)'

    def recipe_image(self, obj):
        """Display recipe image thumbnail in admin list view"""
        try:
            if obj.image:
                return format_html('<img src="{}/-/preview/100x100/" width="50" height="50" style="object-fit: cover; border-radius: 4px;" />',
                                  obj.image.cdn_url)
        except (AttributeError, ValueError):
            pass
        return format_html('<span style="color: #999;">No image</span>')
    recipe_image.short_description = 'Image'

    def total_time_display(self, obj):
        total_time = obj.get_total_time_display()
        return format_html('<span style="color: #6c757d;">{}</span>', total_time)
    total_time_display.short_description = 'Total Time'

    actions = ['make_published', 'make_unpublished', 'make_featured', 'make_unfeatured']

    @admin.action(description='Publish selected recipes')
    def make_published(self, request, queryset):
        updated = queryset.update(is_published=True)
        self.message_user(request, f'{updated} recipes have been published.')

    @admin.action(description='Unpublish selected recipes')
    def make_unpublished(self, request, queryset):
        updated = queryset.update(is_published=False)
        self.message_user(request, f'{updated} recipes have been unpublished.')

    @admin.action(description='Mark selected recipes as featured')
    def make_featured(self, request, queryset):
        updated = queryset.update(is_featured=True)
        self.message_user(request, f'{updated} recipes have been marked as featured.')

    @admin.action(description='Remove featured status from selected recipes')
    def make_unfeatured(self, request, queryset):
        updated = queryset.update(is_featured=False)
        self.message_user(request, f'{updated} recipes are no longer featured.')


@admin.register(RecipePurchase)
class RecipePurchaseAdmin(admin.ModelAdmin):
    list_display = ['user_email', 'recipe_title', 'formatted_price', 'purchased_at', 'download_count', 'order_link']
    list_filter = ['purchased_at', 'recipe__category']
    search_fields = ['user__email', 'user__first_name', 'user__last_name', 'recipe__title']
    readonly_fields = ['user', 'recipe', 'order', 'purchased_at', 'formatted_price']
    date_hierarchy = 'purchased_at'

    def user_email(self, obj):
        return obj.user.email
    user_email.short_description = 'Customer Email'

    def recipe_title(self, obj):
        return obj.recipe.title
    recipe_title.short_description = 'Recipe'

    def formatted_price(self, obj):
        formatted_value = 'KSh {:,.2f}'.format(obj.recipe.price)
        return format_html('<span>{}</span>', formatted_value)
    formatted_price.short_description = 'Price (KES)'

    def order_link(self, obj):
        if obj.order:
            return format_html('<a href="/admin/yummytummy_store/order/{}/change/">Order #{}</a>',
                             obj.order.id, obj.order.get_order_number())
        return format_html('<span style="color: #999;">No order</span>')
    order_link.short_description = 'Order'

    def has_add_permission(self, request):
        return False  # Prevent manual creation of recipe purchases

    def has_delete_permission(self, request, obj=None):
        return False  # Prevent deletion of recipe purchases


# Admin site customization with YummyTummy branding
admin.site.site_header = 'YummyTummy Administration'
admin.site.site_title = 'YummyTummy Admin'
admin.site.index_title = 'YummyTummy Management'
