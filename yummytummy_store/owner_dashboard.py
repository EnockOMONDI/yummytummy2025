from datetime import datetime, time, timedelta
from decimal import Decimal
from functools import wraps
from urllib.parse import urlencode
from zoneinfo import ZoneInfo

from django import forms
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db.models import Count, DecimalField, Exists, ExpressionWrapper, F, OuterRef, Q, Subquery, Sum
from django.shortcuts import render
from django.urls import reverse
from django.utils import timezone

from .models import (
    Order, OrderItem, OrderTrackingStatus, Payment, PaymentAttempt, Product,
    ProductVariant, Recipe, RecipeOrderItem, Refund, NotificationOutbox,
)

NAIROBI = ZoneInfo('Africa/Nairobi')
CAPTURED = ('succeeded', 'partially_refunded', 'refunded')
FULFILLMENT = ('processing', 'packaging', 'shipped', 'out_for_delivery', 'delivered', 'cancelled')


def owner_required(view):
    @staff_member_required
    @wraps(view)
    def wrapped(request, *args, **kwargs):
        if not request.user.has_perm('yummytummy_store.view_owner_dashboard'):
            raise PermissionDenied
        return view(request, *args, **kwargs)
    return wrapped


class PeriodForm(forms.Form):
    period = forms.ChoiceField(choices=[
        ('month', 'This month'), ('today', 'Today'), ('week', 'This week'),
        ('all', 'All time'), ('custom', 'Custom dates'),
    ])
    start = forms.DateField(required=False, widget=forms.DateInput(attrs={'type': 'date'}))
    end = forms.DateField(required=False, widget=forms.DateInput(attrs={'type': 'date'}))

    def clean(self):
        values = super().clean()
        if values.get('period') == 'custom':
            if not values.get('start') or not values.get('end'):
                raise forms.ValidationError('Choose both dates for a custom period.')
            if values['start'] > values['end']:
                raise forms.ValidationError('The start date must not be after the end date.')
        return values


def period_context(request):
    form = PeriodForm(request.GET if 'period' in request.GET else {'period': 'month'})
    valid = form.is_valid()
    values = form.cleaned_data if valid else {'period': 'month'}
    today = timezone.localdate(timezone=NAIROBI)
    period = values['period']
    start, end = None, None
    if period == 'today':
        start = end = today
    elif period == 'week':
        start, end = today - timedelta(days=today.weekday()), today
    elif period == 'month':
        start, end = today.replace(day=1), today
    elif period == 'custom':
        start, end = values['start'], values['end']
    bounds = {}
    if start:
        bounds = {
            'gte': datetime.combine(start, time.min, tzinfo=NAIROBI),
            'lt': datetime.combine(end + timedelta(days=1), time.min, tzinfo=NAIROBI),
        }
    query = {'period': period}
    if period == 'custom':
        query.update(start=start.isoformat(), end=end.isoformat())
    return form, bounds, urlencode(query), valid


def dated(queryset, field, bounds):
    return queryset.filter(**{f'{field}__{lookup}': value for lookup, value in bounds.items()})


def total(queryset, field='amount'):
    return queryset.aggregate(value=Sum(field))['value'] or Decimal('0.00')


def datasets(bounds):
    fulfillment = OrderTrackingStatus.objects.filter(
        order_id=OuterRef('pk'), status__in=FULFILLMENT,
    ).order_by('-created_at', '-pk')
    orders = Order.objects.annotate(
        fulfillment=Subquery(fulfillment.values('status')[:1]),
        physical=Exists(OrderItem.objects.filter(order_id=OuterRef('pk'))),
    )
    order_period = dated(orders, 'created', bounds)
    captures = Payment.objects.filter(status__in=CAPTURED)
    refunds = Refund.objects.filter(status='succeeded')
    base_stock = Product.objects.filter(is_available=True, track_inventory=True, stock_quantity__lte=5)
    variant_stock = ProductVariant.objects.filter(
        product__is_available=True, product__track_inventory=True, stock_quantity__lte=5,
    )
    stale = timezone.now() - timedelta(minutes=15)
    result = {
        'captures': ('Captured payments', dated(captures, 'completed_at', bounds), 'money-bill-wave'),
        'refunds': ('Successful refunds', dated(refunds, 'completed_at', bounds), 'undo'),
        'orders': ('Orders created', order_period, 'shopping-cart'),
        'paid_orders': ('Paid orders created', order_period.filter(
            Exists(Payment.objects.filter(order_id=OuterRef('pk'), status__in=CAPTURED))
        ), 'check-circle'),
        'products': ('Products', Product.objects.all(), 'box'),
        'recipes': ('Recipes', Recipe.objects.all(), 'book'),
        'customers': ('Registered customer accounts', User.objects.filter(is_staff=False, is_superuser=False), 'users'),
        'failed': ('Failed payments', Payment.objects.filter(is_current=True, status='failed'), 'exclamation-circle'),
        'pending': ('Pending payments', Payment.objects.filter(is_current=True, status='pending'), 'clock'),
        'processing': ('Processing payments', Payment.objects.filter(is_current=True, status='processing'), 'clock'),
        'refund_requests': ('Requested refunds', Refund.objects.filter(status='requested'), 'undo'),
        'notifications': ('Queued, failed or stalled notifications', NotificationOutbox.objects.filter(
            Q(status__in=['queued', 'failed']) | Q(status='processing', processed_at__lt=stale)
            | Q(status='processing', processed_at__isnull=True)
        ), 'envelope'),
        'base_stock': ('Low base stock (5 or fewer)', base_stock, 'boxes'),
        'variant_stock': ('Low variant stock (5 or fewer)', variant_stock, 'boxes'),
        'undated_captures': ('Captured payments without completion dates', captures.filter(completed_at__isnull=True), 'calendar'),
        'undated_refunds': ('Successful refunds without completion dates', refunds.filter(completed_at__isnull=True), 'calendar'),
    }
    for status in FULFILLMENT:
        result['fulfillment_' + status] = (
            status.replace('_', ' ').title(), orders.filter(physical=True, fulfillment=status), 'truck',
        )
    result['fulfillment_unstarted'] = (
        'Not started', orders.filter(physical=True, fulfillment__isnull=True), 'box-open',
    )
    # Use the same image resolution rules as the storefront, without external requests.
    missing_products = [p.pk for p in Product.objects.filter(is_available=True) if not p.get_image_url()]
    missing_recipes = [r.pk for r in Recipe.objects.filter(is_published=True) if not r.get_image_url() or not r.pdf_file]
    result['product_media'] = ('Products missing images', Product.objects.filter(pk__in=missing_products), 'image')
    result['recipe_media'] = ('Recipes missing image or PDF', Recipe.objects.filter(pk__in=missing_recipes), 'file')
    return result


def record_link(user, obj):
    if isinstance(obj, ProductVariant):
        obj = obj.product
    opts = obj._meta
    if not user.has_perm(f'{opts.app_label}.view_{opts.model_name}'):
        return ''
    return reverse(f'admin:{opts.app_label}_{opts.model_name}_change', args=[obj.pk])


def record_row(user, obj, section):
    label = str(obj)
    if isinstance(obj, Order):
        label = obj.get_order_number()
    stamp = getattr(obj, 'completed_at', None) or getattr(obj, 'created_at', None) or getattr(obj, 'created', None)
    if section in ('captures', 'refunds', 'undated_captures', 'undated_refunds'):
        stamp = obj.completed_at
    status = obj.get_status_display() if hasattr(obj, 'get_status_display') else ''
    if isinstance(obj, Order):
        status = obj.get_payment_status_display()
    return {
        'label': label, 'url': record_link(user, obj), 'status': status,
        'amount': getattr(obj, 'amount', getattr(obj, 'total_amount', None)), 'stock': getattr(obj, 'stock_quantity', None),
        'date': stamp,
    }


ACTION_GROUPS = {
    'Sales': [('Orders', 'order'), ('Offline orders', 'offline_orders_dashboard'), ('Create manual order', 'create_offline_order')],
    'Catalog': [('Products', 'product'), ('Categories', 'category'), ('Ingredients', 'ingredient'),
                ('Recipes', 'recipe'), ('Recipe categories', 'recipecategory'), ('Recipe sales', 'recipepurchase')],
    'Finance': [('Payments', 'payment'), ('Refunds', 'refund'), ('Coupons', 'coupon'), ('Coupon usage', 'couponusage')],
    'Operations': [('Tracking history', 'ordertrackingstatus'), ('Notifications', 'notificationoutbox'),
                   ('Payment attempts', 'paymentattempt'), ('Provider events', 'paymentproviderevent')],
    'Access': [('Users', 'auth_user'), ('Roles', 'auth_group')],
}


def quick_actions(user):
    groups = []
    for title, actions in ACTION_GROUPS.items():
        items = []
        for label, name in actions:
            if name in ('offline_orders_dashboard', 'create_offline_order'):
                if not (user.has_perm('yummytummy_store.add_order') and user.has_perm('yummytummy_store.view_product')):
                    continue
                url = reverse('yummytummy_store:' + name)
            else:
                app, model = ('auth', name[5:]) if name.startswith('auth_') else ('yummytummy_store', name)
                if not user.has_perm(f'{app}.view_{model}'):
                    continue
                url = reverse(f'admin:{app}_{model}_changelist')
            items.append({'label': label, 'url': url})
        if items:
            groups.append({'title': title, 'items': items})
    return groups


@owner_required
def dashboard(request, section=None):
    form, bounds, query, valid = period_context(request)
    data = datasets(bounds)
    def link(key):
        return reverse('yummytummy_store:owner_records', args=[key]) + '?' + query
    def metric(key, money=False, note=''):
        title, qs, icon = data[key]
        value = total(qs) if money else qs.count()
        return {'title': title, 'value': value, 'money': money, 'url': link(key), 'note': note, 'icon': icon}
    context = {'period_form': form, 'period_query': query, 'current_time': timezone.now(),
               'quick_actions': quick_actions(request.user)}
    if section:
        from django.http import Http404
        if section not in data:
            raise Http404
        title, qs, _ = data[section]
        page = Paginator(qs.order_by('-pk'), 30).get_page(request.GET.get('page'))
        opts = qs.model._meta
        manage_url = ''
        if opts.model_name == 'productvariant':
            if request.user.has_perm('yummytummy_store.view_product'):
                manage_url = reverse('admin:yummytummy_store_product_changelist')
        elif request.user.has_perm(f'{opts.app_label}.view_{opts.model_name}'):
            manage_url = reverse(f'admin:{opts.app_label}_{opts.model_name}_changelist')
        context.update(record_title=title, page=page, manage_url=manage_url,
                       records=[record_row(request.user, obj, section) for obj in page])
        return render(request, 'yummytummy_store/admin/owner_records.html', context, status=200 if valid else 400)
    captured = total(data['captures'][1])
    refunded = total(data['refunds'][1])
    metrics = [
        metric('captures', True, 'By capture date'),
        metric('refunds', True, 'By refund completion date'),
        {'title': 'Net collections', 'value': captured - refunded, 'money': True, 'icon': 'wallet',
         'note': 'Captures less refunds in this period; not profit'},
        metric('orders', note='By order creation date'),
        metric('paid_orders', note='Includes subsequently refunded orders'),
        metric('products', note=f"{Product.objects.filter(is_available=True).count()} available; current catalog"),
        metric('recipes', note=f"{Recipe.objects.filter(is_published=True).count()} published; current catalog"),
        metric('customers', note='Current registered accounts; excludes guest buyers'),
    ]
    exceptions = []
    for key in ('failed', 'pending', 'processing', 'refund_requests', 'notifications', 'base_stock',
                'variant_stock', 'product_media', 'recipe_media', 'undated_captures', 'undated_refunds'):
        item = metric(key)
        if item['value']:
            exceptions.append(item)
    paid_ids = data['captures'][1].values('order_id')
    line_value = ExpressionWrapper(F('price') * F('quantity'), output_field=DecimalField(max_digits=14, decimal_places=2))
    products = list(OrderItem.objects.filter(order_id__in=paid_ids).values('product_id', 'product_name').annotate(
        units=Sum('quantity'), gross=Sum(line_value)).order_by('-units')[:5])
    recipes = list(RecipeOrderItem.objects.filter(order_id__in=paid_ids).values('recipe_id', 'recipe_title').annotate(
        units=Sum('quantity'), gross=Sum(line_value)).order_by('-units')[:5])
    for rows, model, field in ((products, 'product', 'product_id'), (recipes, 'recipe', 'recipe_id')):
        for row in rows:
            row['url'] = reverse(f'admin:yummytummy_store_{model}_change', args=[row[field]]) if request.user.has_perm(f'yummytummy_store.view_{model}') else ''
    recent = list(data['orders'][1].prefetch_related('payments').order_by('-created', '-pk')[:10])
    for order in recent:
        order.owner_url = record_link(request.user, order)
        order.delivery_label = (order.fulfillment or 'not_started').replace('_', ' ').title() if order.physical else 'Digital only'
        current = next((p for p in order.payments.all() if p.is_current), None)
        order.owner_payment_label = current.get_status_display() if current else 'No payment record'
    attempts = dated(PaymentAttempt.objects.filter(payment__method='mpesa'), 'initiated_at', bounds)
    finished = attempts.filter(status__in=('succeeded', 'failed', 'cancelled'))
    attempt_count = finished.count()
    context.update(
        metrics=metrics, exceptions=exceptions, recent_orders=recent,
        fulfillment=[metric('fulfillment_' + s) for s in ('unstarted',) + FULFILLMENT],
        product_sales=products, recipe_sales=recipes,
        mpesa_rate=round(finished.filter(status='succeeded').count() * 100 / attempt_count, 1) if attempt_count else None,
        mpesa_attempt_count=attempt_count, mpesa_active=attempts.exclude(status__in=('succeeded', 'failed', 'cancelled')).count(),
        activity=OrderTrackingStatus.objects.select_related('order', 'created_by').order_by('-created_at')[:8],
    )
    return render(request, 'yummytummy_store/admin/dashboard.html', context, status=200 if valid else 400)


@owner_required
def guide(request):
    return render(request, 'yummytummy_store/admin/how_it_works.html')
