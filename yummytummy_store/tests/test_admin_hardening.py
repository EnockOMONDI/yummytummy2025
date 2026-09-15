import json
from decimal import Decimal
from unittest.mock import patch

from django.contrib import admin
from django.contrib.auth.models import Group, User
from django.core import signing
from django.http import QueryDict
from django.test import RequestFactory
from django.test import TestCase, override_settings
from django.urls import reverse

from yummytummy_store.admin import RefundAdmin
from yummytummy_store.admin_forms import ProductAdminForm, RecipeAdminForm, RefundAdminForm
from yummytummy_store.forms import PaymentForm
from yummytummy_store.models import (
    Category,
    CouponUsage,
    Order,
    OrderItem,
    OrderTrackingStatus,
    NotificationOutbox,
    Payment,
    PaymentAttempt,
    PaymentProviderEvent,
    Product,
    Recipe,
    RecipeCategory,
    RecipeOrderItem,
    RecipePurchase,
    Refund,
)
from yummytummy_store.services import CartPreservationService, OrderTrackingEmailService
from yummytummy_store.notifications import NotificationService
from yummytummy_store.offline_views import send_business_notification
from yummytummy_store.payment_services import PaymentService


class StoreFixtureMixin:
    def create_catalog(self):
        self.category = Category.objects.create(name='Nut Butter', slug='nut-butter')
        self.product = Product.objects.create(
            category=self.category,
            name='Peanut Butter',
            slug='peanut-butter',
            description='Fresh peanut butter',
            price=Decimal('500.00'),
            is_available=True,
        )

    def create_order(self, **overrides):
        values = {
            'first_name': 'Test',
            'last_name': 'Buyer',
            'email': 'buyer@example.com',
            'phone': '0712345678',
            'address': 'Nairobi',
            'payment_method': 'mpesa',
            'payment_status': 'failed',
            'subtotal_amount': Decimal('500.00'),
            'total_amount': Decimal('500.00'),
        }
        values.update(overrides)
        return Order.objects.create(**values)


class AdminAccessTests(StoreFixtureMixin, TestCase):
    def setUp(self):
        self.create_catalog()
        self.superuser = User.objects.create_superuser(
            username='admin@example.com',
            email='admin@example.com',
            password='test-admin-password',
        )

    def test_operational_pages_require_staff(self):
        for name in ('how_it_works', 'admin_dashboard', 'test_mpesa_auth'):
            response = self.client.get(reverse(f'yummytummy_store:{name}'))
            self.assertEqual(response.status_code, 302)
            self.assertIn('/admin/login/', response['Location'])

    def test_coupon_usage_cannot_be_added_from_admin(self):
        self.client.force_login(self.superuser)
        response = self.client.get(reverse('admin:yummytummy_store_couponusage_add'))
        self.assertEqual(response.status_code, 403)
        self.assertFalse(CouponUsage.objects.exists())

    def test_admin_product_form_sanitizes_rich_text(self):
        form = ProductAdminForm(data={
            'category': self.category.pk,
            'name': 'Safe Product',
            'slug': 'safe-product',
            'description': '<p>Good</p><script>alert(1)</script>',
            'price': '250.00',
            'size': '400 g',
            'track_inventory': False,
            'stock_quantity': 0,
            'is_available': True,
            'is_featured': False,
            'feature_type': '',
        })
        self.assertTrue(form.is_valid(), form.errors)
        product = form.save()
        self.assertIn('<p>Good</p>', product.description)
        self.assertNotIn('<script', product.description)

    def test_manual_payment_action_only_confirms_offline_methods(self):
        offline_order = self.create_order(payment_method='offline', payment_status='pending')
        mpesa_order = self.create_order(email='second@example.com', payment_status='pending')
        offline_payment = Payment.objects.create(
            order=offline_order, method='offline', status='pending', amount=offline_order.total_amount,
        )
        mpesa_payment = Payment.objects.create(
            order=mpesa_order, method='mpesa', status='pending', amount=mpesa_order.total_amount,
        )

        self.client.force_login(self.superuser)
        response = self.client.post(reverse('admin:yummytummy_store_payment_changelist'), {
            'action': 'mark_manual_payment_received',
            'confirm': 'yes',
            '_selected_action': [offline_payment.pk, mpesa_payment.pk],
        })
        self.assertEqual(response.status_code, 302)
        offline_payment.refresh_from_db()
        mpesa_payment.refresh_from_db()
        self.assertEqual(offline_payment.status, 'succeeded')
        self.assertEqual(mpesa_payment.status, 'pending')
        self.assertTrue(OrderTrackingStatus.objects.filter(
            order=offline_order, status='payment_confirmed', created_by=self.superuser,
        ).exists())

    def test_refund_form_only_offers_captured_payments(self):
        succeeded_order = self.create_order(payment_status='completed')
        pending_order = self.create_order(email='pending@example.com', payment_status='pending')
        succeeded = Payment.objects.create(
            order=succeeded_order,
            method='mpesa',
            status='succeeded',
            amount=succeeded_order.total_amount,
            provider_reference='CAPTURED-123',
        )
        pending = Payment.objects.create(
            order=pending_order,
            method='mpesa',
            status='pending',
            amount=pending_order.total_amount,
        )

        form = RefundAdminForm()

        self.assertIn(succeeded, form.fields['payment'].queryset)
        self.assertNotIn(pending, form.fields['payment'].queryset)

    def test_refund_admin_requires_provider_reference_and_syncs_payment_status(self):
        order = self.create_order(payment_status='completed')
        payment = Payment.objects.create(
            order=order,
            method='mpesa',
            status='succeeded',
            amount=order.total_amount,
            provider_reference='CAPTURED-456',
        )
        self.client.force_login(self.superuser)
        add_url = reverse('admin:yummytummy_store_refund_add')

        invalid_response = self.client.post(add_url, {
            'payment': payment.pk,
            'amount': '100.00',
            'reason': 'Customer request',
            'status': 'succeeded',
            'provider_reference': '',
            '_save': 'Save',
        })
        self.assertEqual(invalid_response.status_code, 200)
        self.assertFalse(Refund.objects.exists())

        response = self.client.post(add_url, {
            'payment': payment.pk,
            'amount': '100.00',
            'reason': 'Customer request',
            'status': 'succeeded',
            'provider_reference': 'REFUND-123',
            '_save': 'Save',
        })
        self.assertEqual(response.status_code, 302)
        refund = Refund.objects.get()
        self.assertEqual(refund.requested_by, self.superuser)
        self.assertEqual(refund.approved_by, self.superuser)
        payment.refresh_from_db()
        order.refresh_from_db()
        self.assertEqual(payment.status, 'partially_refunded')
        self.assertEqual(order.payment_status, 'completed')

        response = self.client.post(
            reverse('admin:yummytummy_store_refund_change', args=[refund.pk]),
            {
                'amount': '100.00',
                'reason': 'Customer request',
                'status': 'cancelled',
                'provider_reference': 'REFUND-123',
                '_save': 'Save',
            },
        )
        self.assertEqual(response.status_code, 302)
        refund.refresh_from_db()
        payment.refresh_from_db()
        self.assertEqual(refund.status, 'cancelled')
        self.assertIsNone(refund.approved_by)
        self.assertEqual(payment.status, 'succeeded')

    def test_non_superuser_cannot_approve_refunds_from_admin(self):
        finance_user = User.objects.create_user(
            username='finance@example.com',
            email='finance@example.com',
            password='finance-password',
            is_staff=True,
        )
        finance_user.groups.add(Group.objects.get(name='Finance Team'))
        request = RequestFactory().get('/admin/yummytummy_store/refund/add/')
        request.user = finance_user
        refund_admin = RefundAdmin(Refund, admin.site)

        readonly = refund_admin.get_readonly_fields(request)

        self.assertIn('status', readonly)
        self.assertIn('provider_reference', readonly)

    def test_existing_refund_cannot_be_approved_without_reference(self):
        order = self.create_order(payment_status='completed')
        payment = Payment.objects.create(order=order, method='mpesa', status='succeeded', amount=order.total_amount)
        refund = Refund.objects.create(payment=payment, amount='100.00', reason='Return', requested_by=self.superuser)
        self.client.force_login(self.superuser)
        response = self.client.post(reverse('admin:yummytummy_store_refund_change', args=[refund.pk]), {
            'amount': '100.00', 'reason': 'Return', 'status': 'succeeded', 'provider_reference': '', '_save': 'Save',
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Enter the M-Pesa refund reference')
        refund.refresh_from_db()
        self.assertEqual(refund.status, 'requested')

    def test_finance_cannot_tamper_with_approved_refund(self):
        order = self.create_order(payment_status='completed')
        payment = Payment.objects.create(order=order, method='mpesa', status='partially_refunded', amount=order.total_amount)
        refund = Refund.objects.create(
            payment=payment, amount='100.00', reason='Return', status='succeeded',
            provider_reference='REFUND-LOCKED', requested_by=self.superuser, approved_by=self.superuser,
        )
        finance = User.objects.create_user(username='finance-tamper', is_staff=True)
        finance.groups.add(Group.objects.get(name='Finance Team'))
        self.client.force_login(finance)
        response = self.client.post(reverse('admin:yummytummy_store_refund_change', args=[refund.pk]), {
            'amount': '500.00', 'reason': 'Changed', 'status': 'cancelled', 'provider_reference': '', '_save': 'Save',
        })
        self.assertEqual(response.status_code, 302)
        refund.refresh_from_db()
        payment.refresh_from_db()
        self.assertEqual(refund.amount, Decimal('100.00'))
        self.assertEqual(refund.reason, 'Return')
        self.assertEqual(refund.status, 'succeeded')
        self.assertEqual(refund.provider_reference, 'REFUND-LOCKED')
        self.assertEqual(refund.approved_by, self.superuser)
        self.assertEqual(payment.status, 'partially_refunded')


class EmailConfigurationTests(StoreFixtureMixin, TestCase):
    def setUp(self):
        self.create_catalog()
        self.order = self.create_order(payment_method='offline', payment_status='pending')
        OrderItem.objects.create(
            order=self.order,
            product=self.product,
            price=Decimal('500.00'),
            quantity=1,
        )
        self.sales_user = User.objects.create_user(
            username='sales@example.com',
            email='sales@example.com',
            password='test-sales-password',
            first_name='Sales',
            last_name='User',
        )

    @override_settings(
        EMAIL_BACKEND='anymail.backends.resend.EmailBackend',
        RESEND_API_KEY='test-key',
        DEFAULT_FROM_EMAIL='YummyTummy <info@yummytummy.co.ke>',
        ADMIN_EMAIL='info@yummytummy.co.ke',
        ORDERS_EMAIL='orders@yummytummy.co.ke',
        BUSINESS_NOTIFICATION_EMAIL='orders@yummytummy.co.ke',
    )
    def test_resend_email_settings_are_available(self):
        from django.conf import settings

        self.assertEqual(settings.EMAIL_BACKEND, 'anymail.backends.resend.EmailBackend')
        self.assertEqual(settings.RESEND_API_KEY, 'test-key')
        self.assertEqual(settings.DEFAULT_FROM_EMAIL, 'YummyTummy <info@yummytummy.co.ke>')
        self.assertEqual(settings.ADMIN_EMAIL, 'info@yummytummy.co.ke')
        self.assertEqual(settings.ORDERS_EMAIL, 'orders@yummytummy.co.ke')

    @override_settings(
        DEFAULT_FROM_EMAIL='YummyTummy <info@yummytummy.co.ke>',
        ADMIN_EMAIL='info@yummytummy.co.ke',
        ORDERS_EMAIL='orders@yummytummy.co.ke',
        BUSINESS_NOTIFICATION_EMAIL='legacy@example.com',
    )
    @patch('yummytummy_store.offline_views.send_mail')
    def test_offline_order_alert_goes_to_orders_inbox(self, send_mail):
        send_business_notification(self.order, self.sales_user)

        self.assertEqual(send_mail.call_args.kwargs['recipient_list'], ['orders@yummytummy.co.ke'])
        self.assertEqual(send_mail.call_args.kwargs['from_email'], 'YummyTummy <info@yummytummy.co.ke>')


class PaymentBoundaryTests(StoreFixtureMixin, TestCase):
    def setUp(self):
        self.create_catalog()
        self.order = self.create_order()
        OrderItem.objects.create(
            order=self.order,
            product=self.product,
            product_name=self.product.name,
            price=self.product.price,
            quantity=1,
        )
        CartPreservationService.preserve_cart_for_order(self.order)

    def test_payment_retry_requires_signed_token(self):
        url = reverse('yummytummy_store:payment_retry', args=[self.order.pk])
        response = self.client.get(url)
        self.assertRedirects(response, reverse('yummytummy_store:guest_order_tracking'))
        self.assertNotIn('checkout_data', self.client.session)

        token = signing.dumps(
            {'order_id': self.order.pk, 'email': self.order.email},
            salt='yummytummy.payment-retry',
            compress=True,
        )
        response = self.client.get(url, {'token': token})
        self.assertRedirects(response, reverse('yummytummy_store:payment'))
        self.assertEqual(self.client.session['cart'][f'{self.product.pk}_base']['quantity'], 1)

    @override_settings(MPESA_ALLOW_LIVE_IN_DEBUG=True)
    @patch('yummytummy_store.views.MPesaService.initiate_stk_push')
    def test_payment_retry_reuses_original_order(self, initiate_stk_push):
        initiate_stk_push.return_value = {
            'success': True,
            'checkout_request_id': 'retry-checkout-123',
            'merchant_request_id': 'retry-merchant-123',
        }
        token = signing.dumps(
            {'order_id': self.order.pk, 'email': self.order.email},
            salt='yummytummy.payment-retry',
            compress=True,
        )
        self.client.get(
            reverse('yummytummy_store:payment_retry', args=[self.order.pk]),
            {'token': token},
        )

        response = self.client.post(reverse('yummytummy_store:payment'), {
            'payment_method': 'mpesa',
            'mpesa_phone': '0712345678',
            'terms_accepted': 'on',
        })

        self.assertRedirects(
            response,
            reverse('yummytummy_store:order_confirmation'),
            fetch_redirect_response=False,
        )
        self.assertEqual(Order.objects.count(), 1)
        self.assertEqual(self.order.payments.get(is_current=True).attempts.count(), 1)
        self.assertEqual(self.client.session['order_id'], self.order.pk)

    def test_checkout_only_offers_implemented_payment_methods(self):
        self.assertEqual(PaymentForm.PAYMENT_CHOICES, [('mpesa', 'M-Pesa')])

    def _prepare_attempt(self):
        payment = Payment.objects.create(
            order=self.order,
            method='mpesa',
            status='processing',
            amount=self.order.total_amount,
        )
        attempt = PaymentAttempt.objects.create(
            payment=payment,
            sequence=1,
            status='processing',
            checkout_request_id='checkout-123',
            merchant_request_id='merchant-123',
        )
        return payment, attempt

    def _callback_payload(self, amount='500.00', receipt='RECEIPT-123'):
        return {
            'Body': {
                'stkCallback': {
                    'MerchantRequestID': 'merchant-123',
                    'CheckoutRequestID': 'checkout-123',
                    'ResultCode': 0,
                    'ResultDesc': 'Processed',
                    'CallbackMetadata': {'Item': [
                        {'Name': 'Amount', 'Value': amount},
                        {'Name': 'MpesaReceiptNumber', 'Value': receipt},
                        {'Name': 'PhoneNumber', 'Value': 254700000000},
                    ]},
                }
            }
        }

    def test_callback_is_idempotent_and_persists_only_redacted_metadata(self):
        payment, attempt = self._prepare_attempt()
        payload = self._callback_payload()
        url = reverse('yummytummy_store:mpesa_callback')

        first = self.client.post(url, json.dumps(payload), content_type='application/json')
        second = self.client.post(url, json.dumps(payload), content_type='application/json')
        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(PaymentProviderEvent.objects.count(), 1)

        payment.refresh_from_db()
        attempt.refresh_from_db()
        event = PaymentProviderEvent.objects.get()
        self.assertEqual(payment.status, 'succeeded')
        self.assertEqual(attempt.status, 'succeeded')
        self.assertNotIn('254700000000', json.dumps(event.redacted_payload))

    def test_callback_rejects_amount_mismatch(self):
        payment, attempt = self._prepare_attempt()
        response = self.client.post(
            reverse('yummytummy_store:mpesa_callback'),
            json.dumps(self._callback_payload(amount='1.00')),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)
        payment.refresh_from_db()
        attempt.refresh_from_db()
        event = PaymentProviderEvent.objects.get()
        self.assertEqual(event.processing_status, 'failed')
        self.assertEqual(payment.status, 'processing')
        self.assertEqual(attempt.status, 'processing')

    def test_callback_retries_after_processing_transaction_rolls_back(self):
        payment, attempt = self._prepare_attempt()
        url = reverse('yummytummy_store:mpesa_callback')
        payload = json.dumps(self._callback_payload())
        with patch('yummytummy_store.views.PaymentService.mark_succeeded', side_effect=RuntimeError('Interrupted')):
            with self.assertRaises(RuntimeError):
                self.client.post(url, payload, content_type='application/json')
        self.assertEqual(PaymentProviderEvent.objects.get().processing_status, 'received')
        payment.refresh_from_db()
        self.assertEqual(payment.status, 'processing')

        response = self.client.post(url, payload, content_type='application/json')
        self.assertEqual(response.status_code, 200)
        payment.refresh_from_db()
        self.assertEqual(payment.status, 'succeeded')
        self.assertEqual(PaymentProviderEvent.objects.get().processing_status, 'processed')
        self.client.post(url, payload, content_type='application/json')
        self.assertEqual(PaymentProviderEvent.objects.count(), 1)
        self.assertEqual(OrderTrackingStatus.objects.filter(order=self.order, status='payment_confirmed').count(), 1)


class OfflineOrderTrustTests(StoreFixtureMixin, TestCase):
    def setUp(self):
        self.create_catalog()
        self.sales_user = User.objects.create_user(
            username='sales@example.com',
            email='sales@example.com',
            password='sales-password',
            is_staff=True,
        )
        self.sales_user.groups.add(Group.objects.get(name='Sales Team'))
        self.client.force_login(self.sales_user)

    def test_offline_order_ignores_submitted_price(self):
        response = self.client.post(reverse('yummytummy_store:create_offline_order'), {
            'customer_type': 'individual',
            'first_name': 'Walk-in',
            'last_name': 'Buyer',
            'email': 'walkin@example.com',
            'phone': '0712345678',
            'delivery_address': 'Westlands',
            'delivery_city': 'Nairobi',
            'delivery_county': 'Nairobi',
            'order_items': json.dumps([{
                'product_id': self.product.pk,
                'variant_id': None,
                'quantity': 2,
                'price': '1.00',
            }]),
            'order_notes': 'Call on arrival',
        })
        order = Order.objects.get(email='walkin@example.com')
        self.assertRedirects(
            response,
            reverse('yummytummy_store:offline_order_success', args=[order.pk]),
        )
        item = order.items.get()
        self.assertEqual(item.price, Decimal('500.00'))
        self.assertEqual(order.total_amount, Decimal('1000.00'))
        self.assertEqual(order.created_by, self.sales_user)
        self.assertEqual(order.payments.get(is_current=True).method, 'offline')


class NotificationOutboxTests(StoreFixtureMixin, TestCase):
    def setUp(self):
        self.create_catalog()
        self.order = self.create_order(payment_method='offline', payment_status='processing')

    @patch('yummytummy_store.services.OrderTrackingEmailService.send_regular_order_confirmation', return_value=True)
    def test_notification_is_claimed_and_sent_only_once(self, send_email):
        outbox = NotificationOutbox.objects.create(
            event_type='payment_confirmation',
            order=self.order,
            recipient=self.order.email,
        )

        self.assertTrue(NotificationService.process(outbox.pk))
        self.assertFalse(NotificationService.process(outbox.pk))
        outbox.refresh_from_db()
        self.assertEqual(outbox.status, 'sent')
        self.assertEqual(outbox.attempts, 1)
        send_email.assert_called_once_with(self.order)

    def test_notification_is_not_queued_without_an_email_recipient(self):
        self.order.email = ''
        self.order.save(update_fields=['email'])
        self.assertIsNone(NotificationService.enqueue_payment_result(self.order, succeeded=False))
        self.assertFalse(NotificationOutbox.objects.exists())


class RecipeOrderItemTests(StoreFixtureMixin, TestCase):
    def setUp(self):
        self.create_catalog()
        self.order = self.create_order(
            payment_status='pending',
            subtotal_amount=Decimal('650.00'),
            total_amount=Decimal('650.00'),
        )
        OrderItem.objects.create(
            order=self.order,
            product=self.product,
            price=Decimal('500.00'),
            quantity=1,
        )
        category = RecipeCategory.objects.create(name='Breakfast', slug='breakfast')
        self.recipe = Recipe.objects.create(
            title='Peanut Oats',
            slug='peanut-oats',
            description='A quick breakfast.',
            category=category,
            ingredients=['Oats', 'Peanut butter'],
            instructions=['Mix', 'Serve'],
            prep_time_minutes=5,
            cook_time_minutes=0,
            servings=1,
            price=Decimal('150.00'),
            is_published=True,
        )

    def test_recipe_line_is_in_totals_email_items_and_retry_cart(self):
        RecipeOrderItem.objects.create(
            order=self.order,
            recipe=self.recipe,
            price=Decimal('150.00'),
            quantity=1,
        )

        self.assertEqual(self.order.get_subtotal(), Decimal('650.00'))
        self.assertEqual(self.order.recalculate_totals(), Decimal('650.00'))
        CartPreservationService.preserve_cart_for_order(self.order)
        self.order.refresh_from_db()
        preserved = json.loads(self.order.preserved_cart_data)
        self.assertEqual(preserved[f'recipe_{self.recipe.pk}']['type'], 'recipe')
        self.assertEqual(
            [item['display_name'] for item in OrderTrackingEmailService.format_order_items_for_email(self.order)],
            ['Peanut Butter', 'Peanut Oats'],
        )

    def test_recipe_access_is_granted_only_after_payment_succeeds(self):
        user = User.objects.create_user(username='recipe@example.com', email='recipe@example.com')
        self.order.user = user
        self.order.save(update_fields=['user'])
        RecipeOrderItem.objects.create(
            order=self.order,
            recipe=self.recipe,
            price=Decimal('150.00'),
            quantity=1,
        )
        payment = Payment.objects.create(
            order=self.order,
            method='mpesa',
            status='processing',
            amount=self.order.total_amount,
        )
        attempt = PaymentAttempt.objects.create(payment=payment, sequence=1, status='processing')

        self.assertFalse(RecipePurchase.objects.filter(user=user, recipe=self.recipe).exists())
        PaymentService.mark_succeeded(attempt, 'RECIPE-RECEIPT')

        self.assertTrue(RecipePurchase.objects.filter(user=user, recipe=self.recipe).exists())

    def test_recipe_admin_array_fields_render_and_submit_as_rows(self):
        form = RecipeAdminForm(instance=self.recipe)
        self.assertEqual(
            form.fields['ingredients'].prepare_value(self.recipe.ingredients),
            ['Oats', 'Peanut butter'],
        )

        data = QueryDict(mutable=True)
        data.update({
            'title': self.recipe.title,
            'slug': self.recipe.slug,
            'description': self.recipe.description,
            'category': str(self.recipe.category_id),
            'prep_time_minutes': '5',
            'cook_time_minutes': '0',
            'servings': '1',
            'difficulty': 'easy',
            'price': '150.00',
            'tags': 'breakfast, quick',
            'preview_content': '<p>Preview</p>',
        })
        data.setlist('ingredients', [' Oats ', ' Peanut butter '])
        data.setlist('instructions', [' Mix ', ' Serve '])

        form = RecipeAdminForm(data=data, instance=self.recipe)
        self.assertTrue(form.is_valid(), form.errors)
        recipe = form.save()
        self.assertEqual(recipe.ingredients, ['Oats', 'Peanut butter'])
        self.assertEqual(recipe.instructions, ['Mix', 'Serve'])
