from django.contrib import admin, messages
from django.db import transaction
from django.db.models import Count, F, Q, Sum
from django.urls import reverse
from django.template.response import TemplateResponse
from django.utils import timezone
from django.utils.html import format_html, format_html_join
from pyuploadcare.dj.forms import FileWidget
from pyuploadcare.dj.models import ImageField
from unfold.admin import ModelAdmin, TabularInline

from .admin_forms import (
    CategoryAdminForm, CouponAdminForm, IngredientAdminForm, ProductAdminForm,
    ProductIngredientInlineFormSet, RecipeAdminForm, RecipeCategoryAdminForm,
    RefundAdminForm,
)
from .models import (
    AutoCreatedAccount, Category, Coupon, CouponUsage, Ingredient,
    NotificationOutbox, Order, OrderItem, OrderTrackingStatus, Payment,
    PaymentAttempt, PaymentProviderEvent, Product, ProductIngredient,
    ProductVariant, Recipe, RecipeCategory, RecipeOrderItem, RecipePurchase, Refund,
)
from .notifications import NotificationService
from .payment_services import PaymentService


admin.site.site_header = 'YummyTummy Operations'
admin.site.site_title = 'YummyTummy Operations'
admin.site.index_title = 'Store administration'


def money(value):
    return '-' if value is None else f'KSh {value:,.2f}'


def confirm_action(request, queryset, title):
    if request.POST.get('confirm') == 'yes':
        return None
    return TemplateResponse(request, 'admin/confirm_operation.html', {
        **admin.site.each_context(request),
        'title': title, 'objects': queryset, 'action': request.POST.get('action'),
    })


class ProductVariantInline(TabularInline):
    model = ProductVariant
    fields = ('name', 'sku', 'additional_price', 'calculated_price_display', 'stock_quantity')
    readonly_fields = ('calculated_price_display',)
    extra = 0
    show_change_link = True

    @admin.display(description='Selling price')
    def calculated_price_display(self, obj):
        return money(obj.calculated_price) if obj and obj.pk else 'Calculated after saving'


class ProductIngredientInline(TabularInline):
    model = ProductIngredient
    formset = ProductIngredientInlineFormSet
    extra = 0
    autocomplete_fields = ('ingredient',)


@admin.register(Category)
class CategoryAdmin(ModelAdmin):
    form = CategoryAdminForm
    list_display = ('name', 'slug', 'product_count')
    search_fields = ('name',)
    prepopulated_fields = {'slug': ('name',)}

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(_product_count=Count('products'))

    @admin.display(description='Products', ordering='_product_count')
    def product_count(self, obj):
        return obj._product_count


@admin.register(Ingredient)
class IngredientAdmin(ModelAdmin):
    form = IngredientAdminForm
    list_display = ('name', 'product_count')
    search_fields = ('name', 'description')

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(_product_count=Count('products'))

    @admin.display(description='Products', ordering='_product_count')
    def product_count(self, obj):
        return obj._product_count


@admin.register(Product)
class ProductAdmin(ModelAdmin):
    form = ProductAdminForm
    list_display = (
        'name', 'category', 'formatted_price', 'product_image', 'inventory_status',
        'is_available', 'is_featured', 'feature_type', 'updated',
    )
    list_filter = ('is_available', 'is_featured', 'feature_type', 'track_inventory', 'category', 'updated')
    list_editable = ('is_available', 'is_featured', 'feature_type')
    list_select_related = ('category',)
    search_fields = ('name', 'slug', 'description', 'variants__sku')
    prepopulated_fields = {'slug': ('name',)}
    date_hierarchy = 'created'
    inlines = (ProductVariantInline, ProductIngredientInline)
    warn_unsaved_form = True
    formfield_overrides = {
        ImageField: {'widget': FileWidget(attrs={
            'data-images-only': 'true', 'data-preview-step': 'true',
            'data-image-shrink': '1600x1600', 'data-crop': 'free',
            'data-validators': 'image, max-size: 10485760',
        })},
    }
    readonly_fields = ('current_image', 'created', 'updated')
    fieldsets = (
        ('Product', {'fields': ('name', 'slug', 'category', 'description')}),
        ('Price and package', {
            'fields': ('price', 'size'),
            'description': 'Price is the base selling price in KES. Always include a unit in the package size.',
        }),
        ('Inventory', {
            'fields': ('track_inventory', 'stock_quantity'),
            'description': 'When variants exist, manage stock on each variant. Base stock applies to the standard option.',
        }),
        ('Media', {
            'fields': ('current_image', 'image'),
            'description': 'The current legacy image remains visible until an Uploadcare image replaces it.',
        }),
        ('Storefront status', {'fields': ('is_available', 'is_featured', 'feature_type')}),
        ('Audit', {'fields': ('created', 'updated'), 'classes': ('collapse',)}),
    )
    actions = ('make_available', 'make_unavailable', 'make_featured', 'make_unfeatured')

    @admin.display(description='Price', ordering='price')
    def formatted_price(self, obj):
        return money(obj.price)

    @admin.display(description='Image')
    def product_image(self, obj):
        image_url = obj.get_image_url()
        if image_url:
            return format_html('<img src="{}" alt="" width="48" height="48" style="object-fit:contain" />', image_url)
        return format_html('<span style="color:#b91c1c">Missing</span>')

    @admin.display(description='Current image')
    def current_image(self, obj):
        if not obj:
            return 'Upload an image after saving the product.'
        image_url = obj.get_image_url()
        if image_url:
            return format_html('<img src="{}" alt="{}" style="max-height:240px;max-width:240px;object-fit:contain" />', image_url, obj.name)
        return 'No image is currently attached.'

    @admin.display(description='Inventory')
    def inventory_status(self, obj):
        if not obj.track_inventory:
            return 'Not tracked'
        total = obj.stock_quantity + sum(obj.variants.values_list('stock_quantity', flat=True))
        return format_html('<strong style="color:{}">{} units</strong>', '#15803d' if total else '#b91c1c', total)

    @admin.action(description='Mark selected products as available')
    def make_available(self, request, queryset):
        self.message_user(request, f'{queryset.update(is_available=True)} product(s) made available.')

    @admin.action(description='Mark selected products as unavailable')
    def make_unavailable(self, request, queryset):
        self.message_user(request, f'{queryset.update(is_available=False)} product(s) made unavailable.')

    @admin.action(description='Mark selected products as featured')
    def make_featured(self, request, queryset):
        self.message_user(request, f'{queryset.update(is_featured=True)} product(s) featured.')

    @admin.action(description='Remove featured status')
    def make_unfeatured(self, request, queryset):
        self.message_user(request, f'{queryset.update(is_featured=False)} product(s) unfeatured.')


class OrderItemInline(TabularInline):
    model = OrderItem
    fields = ('product_name', 'variant_name', 'quantity', 'price', 'line_total')
    readonly_fields = fields
    extra = 0
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False

    @admin.display(description='Line total')
    def line_total(self, obj):
        return money(obj.get_cost())


class RecipeOrderItemInline(TabularInline):
    model = RecipeOrderItem
    fields = ('recipe_title', 'quantity', 'price', 'line_total')
    readonly_fields = fields
    extra = 0
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False

    @admin.display(description='Line total')
    def line_total(self, obj):
        return money(obj.get_cost())


class PaymentInline(TabularInline):
    model = Payment
    fields = ('method', 'status', 'amount', 'provider_reference', 'completed_at', 'created_at')
    readonly_fields = fields
    extra = 0
    can_delete = False
    show_change_link = True

    def has_add_permission(self, request, obj=None):
        return False


class TrackingInline(TabularInline):
    model = OrderTrackingStatus
    fields = ('status', 'message', 'created_by', 'created_at')
    readonly_fields = fields
    extra = 0
    can_delete = False
    show_change_link = True

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Order)
class OrderAdmin(ModelAdmin):
    list_display = (
        'order_number', 'customer_name', 'masked_contact', 'payment_summary',
        'fulfillment_status', 'formatted_total', 'source', 'created',
    )
    list_filter = ('payment_status', 'payment_method', 'customer_type', 'created')
    search_fields = (
        '=id', 'first_name', 'last_name', 'email', 'phone', 'transaction_id',
        'mpesa_receipt_number', 'payments__provider_reference',
    )
    date_hierarchy = 'created'
    inlines = (OrderItemInline, RecipeOrderItemInline, PaymentInline, TrackingInline)
    readonly_fields = (
        'order_number', 'user', 'first_name', 'last_name', 'email', 'phone',
        'customer_type', 'business_name', 'address', 'area', 'estate', 'building',
        'landmark', 'city', 'county', 'postal_code', 'payment_status', 'payment_method',
        'mpesa_phone', 'transaction_id', 'mpesa_checkout_request_id',
        'mpesa_merchant_request_id', 'mpesa_receipt_number', 'mpesa_transaction_date',
        'coupon', 'subtotal_amount', 'discount_amount', 'total_amount', 'order_notes',
        'created_by', 'created', 'updated', 'auto_created_account',
        'account_creation_email_sent',
    )
    fieldsets = (
        ('Order identity', {'fields': ('order_number', 'created', 'updated', 'created_by')}),
        ('Customer', {'fields': ('user', ('first_name', 'last_name'), ('email', 'phone'), ('customer_type', 'business_name'))}),
        ('Delivery', {'fields': ('address', 'area', 'estate', 'building', 'landmark', 'city', 'county', 'postal_code')}),
        ('Payment snapshot', {
            'fields': ('payment_method', 'payment_status', 'transaction_id', 'mpesa_phone'),
            'description': 'Payment state is managed through Payment records and provider events.',
        }),
        ('M-Pesa references', {
            'fields': ('mpesa_checkout_request_id', 'mpesa_merchant_request_id', 'mpesa_receipt_number', 'mpesa_transaction_date'),
            'classes': ('collapse',),
        }),
        ('Totals', {'fields': ('subtotal_amount', 'discount_amount', 'total_amount', 'coupon')}),
        ('Notes and account access', {
            'fields': ('order_notes', 'auto_created_account', 'account_creation_email_sent'),
            'classes': ('collapse',),
        }),
    )
    actions = ('mark_processing', 'mark_packaging', 'mark_shipped', 'mark_out_for_delivery', 'mark_delivered')

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    @admin.display(description='Order', ordering='id')
    def order_number(self, obj):
        return obj.get_order_number()

    @admin.display(description='Customer', ordering='first_name')
    def customer_name(self, obj):
        return obj.get_customer_name()

    @admin.display(description='Contact')
    def masked_contact(self, obj):
        phone = f'***{obj.phone[-4:]}' if obj.phone else '-'
        email = '-'
        if obj.email and '@' in obj.email:
            local, domain = obj.email.split('@', 1)
            email = f'{local[:2]}***@{domain}'
        return format_html('{}<br>{}', phone, email)

    @admin.display(description='Payment')
    def payment_summary(self, obj):
        payment = next((item for item in obj.payments.all() if item.is_current), None)
        return payment.get_status_display() if payment else obj.get_payment_status_display()

    @admin.display(description='Fulfillment')
    def fulfillment_status(self, obj):
        latest = obj.get_latest_tracking_status()
        return latest.get_status_display() if latest else 'Not started'

    @admin.display(description='Total', ordering='total_amount')
    def formatted_total(self, obj):
        return money(obj.total_amount)

    @admin.display(description='Source')
    def source(self, obj):
        if obj.created_by_id:
            return 'Offline sales'
        return 'WhatsApp' if obj.payment_method == 'whatsapp' else 'Website'

    def get_queryset(self, request):
        return (
            super().get_queryset(request)
            .select_related('user', 'created_by', 'coupon')
            .prefetch_related('payments', 'tracking_statuses')
        )

    def _transition(self, request, queryset, status, message):
        confirmation = confirm_action(request, queryset, f'Move selected orders to {status.replace("_", " ")}')
        if confirmation:
            return confirmation
        created = 0
        sequence = ('processing', 'packaging', 'shipped', 'out_for_delivery', 'delivered')
        with transaction.atomic():
            for order in Order.objects.filter(pk__in=queryset.values('pk')).select_for_update():
                latest = order.tracking_statuses.filter(status__in=sequence + ('cancelled',)).order_by('-created_at', '-pk').first()
                if not order.items.exists() or (latest and latest.status == 'cancelled'):
                    continue
                if latest and sequence.index(latest.status) >= sequence.index(status):
                    continue
                paid = order.payments.filter(is_current=True, status__in=('succeeded', 'partially_refunded')).exists()
                cod = order.payments.filter(is_current=True, method='cash_on_delivery', status__in=('pending', 'processing')).exists()
                if not (paid or cod):
                    continue
                tracking = OrderTrackingStatus.objects.create(
                    order=order, status=status, message=message, created_by=request.user,
                )
                NotificationService.enqueue_tracking_update(tracking)
                created += 1
        self.message_user(request, f'{created} order(s) moved to {status.replace("_", " ")}. Ineligible orders were skipped.')

    @admin.action(description='Move selected orders to Processing')
    def mark_processing(self, request, queryset):
        return self._transition(request, queryset, 'processing', 'Your order is being prepared.')

    @admin.action(description='Move selected orders to Packaging')
    def mark_packaging(self, request, queryset):
        return self._transition(request, queryset, 'packaging', 'Your order is being packaged.')

    @admin.action(description='Mark selected orders as Shipped')
    def mark_shipped(self, request, queryset):
        return self._transition(request, queryset, 'shipped', 'Your order has been shipped.')

    @admin.action(description='Mark selected orders Out for Delivery')
    def mark_out_for_delivery(self, request, queryset):
        return self._transition(request, queryset, 'out_for_delivery', 'Your order is out for delivery.')

    @admin.action(description='Mark selected orders as Delivered')
    def mark_delivered(self, request, queryset):
        return self._transition(request, queryset, 'delivered', 'Your order has been delivered.')


@admin.register(Payment)
class PaymentAdmin(ModelAdmin):
    list_display = ('order_link', 'method', 'status', 'formatted_amount', 'attempt_count', 'provider_reference', 'created_at')
    list_filter = ('method', 'status', 'created_at')
    search_fields = ('order__id', 'order__email', 'provider_reference', 'attempts__checkout_request_id')
    readonly_fields = (
        'order', 'method', 'status', 'amount', 'currency', 'provider_reference',
        'is_current', 'completed_at', 'created_at', 'updated_at',
    )
    date_hierarchy = 'created_at'
    actions = ('mark_manual_payment_received',)

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('order').annotate(_attempt_count=Count('attempts'))

    @admin.display(description='Order', ordering='order_id')
    def order_link(self, obj):
        url = reverse('admin:yummytummy_store_order_change', args=[obj.order_id])
        return format_html('<a href="{}">{}</a>', url, obj.order.get_order_number())

    @admin.display(description='Amount', ordering='amount')
    def formatted_amount(self, obj):
        return money(obj.amount)

    @admin.display(description='Attempts')
    def attempt_count(self, obj):
        return obj._attempt_count

    @admin.action(description='Confirm selected offline payments as received')
    def mark_manual_payment_received(self, request, queryset):
        confirmation = confirm_action(request, queryset, 'Confirm external payment receipt')
        if confirmation:
            return confirmation
        updated = 0
        skipped = 0
        with transaction.atomic():
            for payment in Payment.objects.filter(pk__in=queryset.values('pk')).select_for_update(of=('self',)).select_related('order'):
                if payment.method not in {'offline', 'cash_on_delivery'} or not payment.is_current or payment.status not in {'pending', 'processing'}:
                    skipped += 1
                    continue
                payment.status = 'succeeded'
                payment.completed_at = timezone.now()
                payment.save(update_fields=['status', 'completed_at', 'updated_at'])
                payment.sync_legacy_order()
                PaymentService.grant_recipe_entitlements(payment.order)
                tracking = OrderTrackingStatus.objects.create(
                    order=payment.order,
                    status='payment_confirmed',
                    message='Manual payment confirmed by the finance team.',
                    created_by=request.user,
                )
                NotificationService.enqueue_tracking_update(tracking)
                updated += 1
        self.message_user(
            request,
            f'{updated} payment(s) confirmed; {skipped} provider, duplicate, or unsupported payment(s) skipped.',
            messages.SUCCESS if updated else messages.WARNING,
        )


class ReadOnlyAuditAdmin(ModelAdmin):
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return request.user.has_perm(f'{self.opts.app_label}.view_{self.opts.model_name}')

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(PaymentAttempt)
class PaymentAttemptAdmin(ReadOnlyAuditAdmin):
    list_display = ('payment', 'sequence', 'status', 'checkout_request_id', 'failure_code', 'initiated_at', 'completed_at')
    list_filter = ('status', 'initiated_at')
    search_fields = ('payment__order__id', 'checkout_request_id', 'merchant_request_id')
    readonly_fields = ('payment', 'sequence', 'status', 'checkout_request_id', 'merchant_request_id', 'failure_code', 'failure_message', 'initiated_at', 'completed_at')


@admin.register(PaymentProviderEvent)
class PaymentProviderEventAdmin(ReadOnlyAuditAdmin):
    list_display = ('provider', 'event_key', 'processing_status', 'payment', 'received_at', 'processed_at')
    list_filter = ('provider', 'processing_status', 'received_at')
    search_fields = ('event_key', 'checkout_request_id', 'payload_hash')
    readonly_fields = ('payment', 'attempt', 'provider', 'event_key', 'event_type', 'checkout_request_id', 'payload_hash', 'redacted_payload', 'processing_status', 'failure_reason', 'received_at', 'processed_at')


@admin.register(Refund)
class RefundAdmin(ModelAdmin):
    form = RefundAdminForm
    list_display = ('payment', 'formatted_amount', 'status', 'requested_by', 'approved_by', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('payment__order__id', 'payment__provider_reference', 'provider_reference')
    readonly_fields = ('requested_by', 'approved_by', 'completed_at', 'created_at', 'updated_at')

    def get_readonly_fields(self, request, obj=None):
        fields = list(self.readonly_fields)
        if obj:
            fields.append('payment')
        if not request.user.is_superuser:
            fields.extend(('status', 'provider_reference'))
            if obj and (obj.status == 'succeeded' or obj.approved_by_id):
                fields.extend(('amount', 'reason'))
        return tuple(fields)

    @admin.display(description='Amount', ordering='amount')
    def formatted_amount(self, obj):
        return money(obj.amount)

    def save_model(self, request, obj, form, change):
        if not obj.pk:
            obj.requested_by = request.user
        if obj.status == 'succeeded':
            if not obj.approved_by_id:
                obj.approved_by = request.user
        else:
            obj.approved_by = None
        obj.full_clean()
        super().save_model(request, obj, form, change)
        PaymentService.sync_refund_status(obj.payment)


@admin.register(Coupon)
class CouponAdmin(ModelAdmin):
    form = CouponAdminForm
    list_display = ('code', 'discount_display', 'validity', 'is_active', 'usage_display', 'minimum_order', 'created')
    list_filter = ('is_active', 'discount_type', 'valid_from', 'valid_to')
    search_fields = ('code',)
    readonly_fields = ('usage_count', 'created', 'updated', 'existing_codes')
    date_hierarchy = 'created'
    fieldsets = (
        ('Coupon', {'fields': ('existing_codes', 'code', 'discount_type', 'discount_value', 'is_active')}),
        ('Validity', {'fields': ('valid_from', 'valid_to', 'min_order_amount')}),
        ('Limits', {'fields': ('usage_limit', 'usage_count', 'per_customer_limit')}),
        ('Audit', {'fields': ('created', 'updated'), 'classes': ('collapse',)}),
    )
    actions = ('activate_coupons', 'deactivate_coupons')

    def get_readonly_fields(self, request, obj=None):
        return (*self.readonly_fields, 'code') if obj else self.readonly_fields

    @admin.display(description='Discount')
    def discount_display(self, obj):
        return obj.get_formatted_discount_value()

    @admin.display(description='Validity')
    def validity(self, obj):
        now = timezone.now()
        if obj.valid_to < now:
            return format_html('<span style="color:#b91c1c">Expired</span>')
        if obj.valid_from > now:
            return 'Scheduled'
        return format_html('<span style="color:#15803d">Current</span>')

    @admin.display(description='Usage')
    def usage_display(self, obj):
        return f'{obj.usage_count} / {obj.usage_limit}'

    @admin.display(description='Minimum order')
    def minimum_order(self, obj):
        return money(obj.min_order_amount)

    @admin.display(description='Existing codes')
    def existing_codes(self, obj):
        queryset = Coupon.objects.exclude(pk=obj.pk if obj else None).order_by('code')
        codes = list(queryset.values_list('code', flat=True)[:20])
        if not codes:
            return 'No other coupon codes.'
        rendered = format_html_join('', '<code style="margin-right:8px">{}</code>', ((code,) for code in codes))
        remaining = max(queryset.count() - len(codes), 0)
        return format_html('{}{}', rendered, f' + {remaining} more' if remaining else '')

    @admin.action(description='Activate selected coupons')
    def activate_coupons(self, request, queryset):
        now = timezone.now()
        invalid = queryset.filter(Q(valid_to__lte=now) | Q(usage_count__gte=F('usage_limit'))).count()
        updated = queryset.filter(valid_to__gt=now, usage_count__lt=F('usage_limit')).update(is_active=True)
        self.message_user(request, f'{updated} coupon(s) activated; {invalid} expired or exhausted coupon(s) skipped.')

    @admin.action(description='Deactivate selected coupons')
    def deactivate_coupons(self, request, queryset):
        self.message_user(request, f'{queryset.update(is_active=False)} coupon(s) deactivated.')


@admin.register(CouponUsage)
class CouponUsageAdmin(ReadOnlyAuditAdmin):
    list_display = ('coupon', 'order_link', 'user', 'formatted_discount', 'used_at')
    list_filter = ('coupon', 'used_at')
    search_fields = ('coupon__code', 'order__id', 'order__email')
    readonly_fields = ('coupon', 'order', 'user', 'discount_amount', 'used_at')

    @admin.display(description='Order')
    def order_link(self, obj):
        url = reverse('admin:yummytummy_store_order_change', args=[obj.order_id])
        return format_html('<a href="{}">{}</a>', url, obj.order.get_order_number())

    @admin.display(description='Discount')
    def formatted_discount(self, obj):
        return money(obj.discount_amount) if obj and obj.discount_amount is not None else '-'


@admin.register(OrderTrackingStatus)
class OrderTrackingStatusAdmin(ModelAdmin):
    list_display = ('order_link', 'status', 'message_preview', 'created_by', 'created_at', 'notification_state')
    list_filter = ('status', 'created_at')
    search_fields = ('order__id', 'order__email', 'message')
    readonly_fields = ('created_by', 'created_at')
    autocomplete_fields = ('order',)
    date_hierarchy = 'created_at'

    def has_change_permission(self, request, obj=None):
        return False

    def get_readonly_fields(self, request, obj=None):
        if obj:
            return ('order', 'status', 'message', 'created_by', 'created_at')
        return self.readonly_fields

    def has_delete_permission(self, request, obj=None):
        return False

    def save_model(self, request, obj, form, change):
        if change:
            return
        obj.created_by = request.user
        super().save_model(request, obj, form, change)
        NotificationService.enqueue_tracking_update(obj)

    @admin.display(description='Order')
    def order_link(self, obj):
        url = reverse('admin:yummytummy_store_order_change', args=[obj.order_id])
        return format_html('<a href="{}">{}</a>', url, obj.order.get_order_number())

    @admin.display(description='Message')
    def message_preview(self, obj):
        return obj.message[:80]

    @admin.display(description='Notification')
    def notification_state(self, obj):
        notification = obj.notifications.order_by('-created_at').first()
        return notification.get_status_display() if notification else 'Not queued'


@admin.register(NotificationOutbox)
class NotificationOutboxAdmin(ReadOnlyAuditAdmin):
    list_display = ('event_type', 'order', 'masked_recipient', 'status', 'attempts', 'created_at', 'processed_at')
    list_filter = ('status', 'event_type', 'created_at')
    search_fields = ('order__id', 'recipient')
    readonly_fields = ('event_type', 'order', 'tracking_status', 'recipient', 'payload', 'status', 'attempts', 'last_error', 'created_at', 'processed_at')
    actions = ('retry_notifications',)

    @admin.display(description='Recipient')
    def masked_recipient(self, obj):
        if not obj.recipient or '@' not in obj.recipient:
            return '-'
        local, domain = obj.recipient.split('@', 1)
        return f'{local[:2]}***@{domain}'

    @admin.action(description='Retry selected queued or failed notifications')
    def retry_notifications(self, request, queryset):
        sent = sum(1 for obj in queryset.filter(status__in=['queued', 'failed']) if NotificationService.process(obj.pk))
        self.message_user(request, f'{sent} notification(s) sent.', messages.SUCCESS)


@admin.register(AutoCreatedAccount)
class AutoCreatedAccountAdmin(ReadOnlyAuditAdmin):
    list_display = ('user', 'created_during_order', 'first_login_completed', 'token_expires', 'created_at')
    list_filter = ('first_login_completed', 'created_at')
    search_fields = ('user__email', 'created_during_order__id')
    readonly_fields = ('user', 'created_during_order', 'initial_password_sent', 'first_login_token', 'token_expires', 'first_login_completed', 'created_at')


@admin.register(RecipeCategory)
class RecipeCategoryAdmin(ModelAdmin):
    form = RecipeCategoryAdminForm
    list_display = ('name', 'slug', 'recipe_count')
    search_fields = ('name',)
    prepopulated_fields = {'slug': ('name',)}

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(_recipe_count=Count('recipes'))

    @admin.display(description='Recipes', ordering='_recipe_count')
    def recipe_count(self, obj):
        return obj._recipe_count


@admin.register(Recipe)
class RecipeAdmin(ModelAdmin):
    form = RecipeAdminForm
    list_display = ('title', 'category', 'formatted_price', 'media_status', 'is_published', 'is_featured', 'updated')
    list_filter = ('is_published', 'is_featured', 'difficulty', 'category', 'updated')
    search_fields = ('title', 'description', 'tags')
    prepopulated_fields = {'slug': ('title',)}
    filter_horizontal = ('related_products',)
    date_hierarchy = 'created'
    warn_unsaved_form = True
    formfield_overrides = ProductAdmin.formfield_overrides
    readonly_fields = ('recipe_image', 'created', 'updated')
    fieldsets = (
        ('Recipe', {'fields': ('title', 'slug', 'category', 'description')}),
        ('Ingredients and method', {
            'fields': ('ingredients', 'instructions'),
            'description': 'Use one row per ingredient and one row per preparation step.',
        }),
        ('Timing', {'fields': ('prep_time_minutes', 'cook_time_minutes', 'servings', 'difficulty')}),
        ('Media and price', {'fields': ('recipe_image', 'image', 'pdf_file', 'price')}),
        ('Discovery', {'fields': ('tags', 'related_products', 'preview_content')}),
        ('Publishing', {
            'fields': ('is_published', 'is_featured'),
            'description': 'Review the image, PDF, preview, and complete instructions before publishing.',
        }),
        ('Audit', {'fields': ('created', 'updated'), 'classes': ('collapse',)}),
    )

    @admin.display(description='Price', ordering='price')
    def formatted_price(self, obj):
        return money(obj.price)

    @admin.display(description='Media')
    def media_status(self, obj):
        missing = []
        if not obj.get_image_url():
            missing.append('image')
        if not obj.pdf_file:
            missing.append('PDF')
        label = f'Missing {", ".join(missing)}' if missing else 'Complete'
        return format_html('<span style="color:{}">{}</span>', '#b91c1c' if missing else '#15803d', label)

    @admin.display(description='Current image')
    def recipe_image(self, obj):
        if obj and obj.get_image_url():
            return format_html('<img src="{}" alt="{}" style="max-height:240px;max-width:240px;object-fit:contain" />', obj.get_image_url(), obj.title)
        return 'No recipe image is attached.'


@admin.register(RecipePurchase)
class RecipePurchaseAdmin(ReadOnlyAuditAdmin):
    list_display = ('user', 'recipe', 'order', 'purchased_at', 'download_count')
    list_filter = ('purchased_at', 'recipe__category')
    search_fields = ('user__email', 'recipe__title', 'order__id')
    readonly_fields = ('user', 'recipe', 'order', 'purchased_at', 'download_count')


@admin.register(RecipeOrderItem)
class RecipeOrderItemAdmin(ReadOnlyAuditAdmin):
    list_display = ('recipe_title', 'order', 'quantity', 'price')
    search_fields = ('recipe_title', 'recipe__title', 'order__id', 'order__email')
    readonly_fields = ('order', 'recipe', 'recipe_title', 'price', 'quantity')
