from datetime import datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

from django.contrib.auth.models import Permission, User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from yummytummy_store.models import (
    Category, NotificationOutbox, Order, OrderItem, OrderTrackingStatus,
    Payment, Product, ProductVariant, Refund,
)
from yummytummy_store.owner_dashboard import datasets


class OwnerDashboardTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_superuser('owner', 'owner@example.com', 'password')
        self.client.force_login(self.owner)
        self.url = reverse('yummytummy_store:admin_dashboard')
        category = Category.objects.create(name='Butter', slug='butter')
        self.product = Product.objects.create(
            category=category, name='Butter', slug='butter', description='Butter',
            price=500, is_available=True, track_inventory=True, stock_quantity=20,
        )

    def order(self, status='succeeded', physical=True, amount='500.00', method='mpesa'):
        order = Order.objects.create(
            first_name='Guest', last_name='Buyer', email='guest@example.com', phone='0712345678',
            address='Nairobi', subtotal_amount=amount, total_amount=amount,
        )
        if physical:
            OrderItem.objects.create(order=order, product=self.product, price=amount, quantity=1)
        payment = Payment.objects.create(
            order=order, amount=amount, method=method, status=status, completed_at=timezone.now(),
        )
        return order, payment

    def test_owner_permission_is_required_and_does_not_grant_model_access(self):
        staff = User.objects.create_user('staff', is_staff=True)
        self.client.force_login(staff)
        self.assertEqual(self.client.get(self.url).status_code, 403)
        self.assertEqual(self.client.get(reverse('yummytummy_store:how_it_works')).status_code, 403)
        staff.user_permissions.add(Permission.objects.get(codename='view_owner_dashboard'))
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['quick_actions'], [])
        self.assertEqual(self.client.get(reverse('admin:yummytummy_store_product_changelist')).status_code, 403)

    def test_collections_include_refunded_captures_and_subtract_only_successful_refunds(self):
        order, payment = self.order(status='partially_refunded')
        Refund.objects.create(payment=payment, amount=100, reason='Return', status='succeeded', requested_by=self.owner)
        Refund.objects.create(payment=payment, amount=50, reason='Pending', requested_by=self.owner)
        response = self.client.get(self.url, {'period': 'all'})
        metrics = {m['title']: m['value'] for m in response.context['metrics']}
        self.assertEqual(metrics['Captured payments'], Decimal('500.00'))
        self.assertEqual(metrics['Successful refunds'], Decimal('100.00'))
        self.assertEqual(metrics['Net collections'], Decimal('400.00'))
        self.assertEqual(metrics['Products'], 1)
        self.assertEqual(metrics['Registered customer accounts'], 0)
        self.assertEqual(metrics['Paid orders created'], 1)

    def test_custom_period_uses_nairobi_day_and_refund_completion_date(self):
        tz = ZoneInfo('Africa/Nairobi')
        _, payment = self.order()
        payment.completed_at = datetime(2026, 8, 31, 23, 59, tzinfo=tz)
        payment.save()
        refund = Refund.objects.create(payment=payment, amount=100, reason='Return', status='succeeded', requested_by=self.owner)
        Refund.objects.filter(pk=refund.pk).update(completed_at=datetime(2026, 9, 1, 0, 0, tzinfo=tz))
        response = self.client.get(self.url, {'period': 'custom', 'start': '2026-09-01', 'end': '2026-09-01'})
        metrics = {m['title']: m for m in response.context['metrics']}
        self.assertEqual(metrics['Captured payments']['value'], 0)
        self.assertEqual(metrics['Successful refunds']['value'], 100)
        self.assertEqual(metrics['Net collections']['value'], -100)
        records = self.client.get(metrics['Successful refunds']['url'])
        self.assertEqual(records.context['page'].paginator.count, 1)
        self.assertEqual(self.client.get(self.url, {'period': 'custom', 'start': 'bad'}).status_code, 400)

    def test_fulfillment_ignores_later_payment_events_and_digital_orders(self):
        order, _ = self.order()
        digital, _ = self.order(physical=False)
        OrderTrackingStatus.objects.create(order=order, status='shipped')
        OrderTrackingStatus.objects.create(order=order, status='payment_confirmed')
        OrderTrackingStatus.objects.create(order=digital, status='shipped')
        data = datasets({})
        self.assertEqual(data['fulfillment_shipped'][1].count(), 1)
        self.assertEqual(data['fulfillment_unstarted'][1].count(), 0)

    def test_catalog_stock_and_notification_exceptions(self):
        ProductVariant.objects.create(product=self.product, name='Small', stock_quantity=2)
        order, payment = self.order()
        NotificationOutbox.objects.create(order=order, event_type='payment_confirmation', recipient=order.email)
        Payment.objects.filter(pk=payment.pk).update(completed_at=None)
        data = datasets({})
        self.assertEqual(data['variant_stock'][1].count(), 1)
        self.assertEqual(data['base_stock'][1].count(), 0)
        self.assertEqual(data['notifications'][1].count(), 1)
        self.assertEqual(data['undated_captures'][1].count(), 1)

    def test_all_dashboard_record_links_resolve_and_empty_guide_renders(self):
        response = self.client.get(self.url, {'period': 'all'})
        self.assertEqual(response.status_code, 200)
        for metric in response.context['metrics'] + response.context['fulfillment'] + response.context['exceptions']:
            if metric.get('url'):
                self.assertEqual(self.client.get(metric['url']).status_code, 200, metric)
        for group in response.context['quick_actions']:
            for action in group['items']:
                self.assertEqual(self.client.get(action['url']).status_code, 200, action)
        guide = self.client.get(reverse('yummytummy_store:how_it_works'))
        self.assertEqual(guide.status_code, 200)
        self.assertNotContains(guide, 'Auto-generated account login credentials')
        products = self.client.get(reverse('admin:yummytummy_store_product_changelist'))
        self.assertContains(products, 'Back to owner dashboard')

    def test_manual_confirmation_cannot_reconfirm_refunded_payment(self):
        _, payment = self.order(status='refunded', method='offline')
        url = reverse('admin:yummytummy_store_payment_changelist')
        data = {'action': 'mark_manual_payment_received', '_selected_action': [payment.pk]}
        self.assertEqual(self.client.post(url, data).status_code, 200)
        self.client.post(url, {**data, 'confirm': 'yes'})
        payment.refresh_from_db()
        self.assertEqual(payment.status, 'refunded')

    def test_order_actions_require_confirmation_and_prevent_backward_or_unpaid_moves(self):
        order, _ = self.order()
        unpaid, _ = self.order(status='pending')
        OrderTrackingStatus.objects.create(order=order, status='delivered')
        url = reverse('admin:yummytummy_store_order_changelist')
        data = {'action': 'mark_processing', '_selected_action': [order.pk, unpaid.pk]}
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 200)
        self.client.post(url, {**data, 'confirm': 'yes'})
        self.assertFalse(OrderTrackingStatus.objects.filter(status='processing').exists())

    def test_refund_completion_date_is_stable_until_cancelled(self):
        _, payment = self.order()
        refund = Refund.objects.create(payment=payment, amount=100, reason='Return', status='succeeded', requested_by=self.owner)
        completed = refund.completed_at
        refund.reason = 'Corrected note'
        refund.save()
        self.assertEqual(refund.completed_at, completed)
        refund.status = 'cancelled'
        refund.save(update_fields=['status'])
        refund.refresh_from_db()
        self.assertIsNone(refund.completed_at)

    def test_editing_legacy_refund_does_not_invent_completion_date(self):
        _, payment = self.order()
        refund = Refund.objects.create(payment=payment, amount=100, reason='Legacy', status='succeeded', requested_by=self.owner)
        Refund.objects.filter(pk=refund.pk).update(completed_at=None)
        refund.refresh_from_db()
        refund.reason = 'Corrected legacy note'
        refund.save()
        self.assertIsNone(refund.completed_at)
        response = self.client.get(reverse('yummytummy_store:owner_records', args=['undated_refunds']))
        self.assertIsNone(response.context['records'][0]['date'])
