import hashlib
import json
from decimal import Decimal, InvalidOperation

from django.db import transaction
from django.db.models import Max, Sum
from django.utils import timezone

from .models import Payment, PaymentAttempt, PaymentProviderEvent, RecipePurchase


class PaymentService:
    """Own payment state while keeping legacy order fields synchronized."""

    @staticmethod
    @transaction.atomic
    def ensure_payment(order, method=None):
        payment = (
            Payment.objects.select_for_update()
            .filter(order=order, is_current=True)
            .first()
        )
        method = method or order.payment_method
        if payment and payment.method == method and payment.amount == order.total_amount:
            return payment

        if payment:
            payment.is_current = False
            payment.save(update_fields=['is_current', 'updated_at'])

        return Payment.objects.create(
            order=order,
            method=method,
            status=PaymentService.legacy_to_payment_status(order.payment_status),
            amount=order.total_amount,
            provider_reference=order.transaction_id,
            is_current=True,
        )

    @staticmethod
    def legacy_to_payment_status(status):
        return {
            'completed': 'succeeded',
            'refunded': 'refunded',
        }.get(status, status if status in {'pending', 'processing', 'failed'} else 'pending')

    @staticmethod
    @transaction.atomic
    def create_attempt(payment):
        locked_payment = Payment.objects.select_for_update().get(pk=payment.pk)
        sequence = locked_payment.attempts.aggregate(max_sequence=Max('sequence'))['max_sequence'] or 0
        return PaymentAttempt.objects.create(payment=locked_payment, sequence=sequence + 1)

    @staticmethod
    @transaction.atomic
    def mark_submitted(attempt, checkout_request_id, merchant_request_id=''):
        attempt = PaymentAttempt.objects.select_for_update().select_related('payment__order').get(pk=attempt.pk)
        attempt.status = 'processing'
        attempt.checkout_request_id = checkout_request_id or None
        attempt.merchant_request_id = merchant_request_id or ''
        attempt.save(update_fields=['status', 'checkout_request_id', 'merchant_request_id'])

        payment = attempt.payment
        payment.status = 'processing'
        payment.save(update_fields=['status', 'updated_at'])
        payment.sync_legacy_order()

        order = payment.order
        order.mpesa_checkout_request_id = checkout_request_id or ''
        order.mpesa_merchant_request_id = merchant_request_id or ''
        order.save(update_fields=['mpesa_checkout_request_id', 'mpesa_merchant_request_id', 'updated'])
        return attempt

    @staticmethod
    @transaction.atomic
    def mark_failed(attempt, failure_code='', failure_message=''):
        attempt = PaymentAttempt.objects.select_for_update().select_related('payment').get(pk=attempt.pk)
        attempt.status = 'failed'
        attempt.failure_code = str(failure_code or '')[:64]
        attempt.failure_message = str(failure_message or 'Payment failed')[:255]
        attempt.completed_at = timezone.now()
        attempt.save(update_fields=['status', 'failure_code', 'failure_message', 'completed_at'])

        payment = attempt.payment
        payment.status = 'failed'
        payment.save(update_fields=['status', 'updated_at'])
        payment.sync_legacy_order()
        return payment

    @staticmethod
    @transaction.atomic
    def mark_succeeded(attempt, provider_reference, completed_at=None):
        attempt = PaymentAttempt.objects.select_for_update().select_related('payment__order').get(pk=attempt.pk)
        attempt.status = 'succeeded'
        attempt.completed_at = completed_at or timezone.now()
        attempt.failure_code = ''
        attempt.failure_message = ''
        attempt.save(update_fields=['status', 'completed_at', 'failure_code', 'failure_message'])

        payment = attempt.payment
        payment.status = 'succeeded'
        payment.provider_reference = provider_reference
        payment.completed_at = completed_at or timezone.now()
        payment.save(update_fields=['status', 'provider_reference', 'completed_at', 'updated_at'])
        payment.sync_legacy_order()
        PaymentService.grant_recipe_entitlements(payment.order)
        return payment

    @staticmethod
    def grant_recipe_entitlements(order):
        """Grant digital access only after the order's payment is confirmed."""
        if not order.user_id:
            return []

        purchases = []
        for line in order.recipe_items.select_related('recipe'):
            purchase, _ = RecipePurchase.objects.get_or_create(
                user_id=order.user_id,
                recipe_id=line.recipe_id,
                defaults={'order': order},
            )
            purchases.append(purchase)
        return purchases

    @staticmethod
    @transaction.atomic
    def sync_refund_status(payment):
        """Derive payment state from its successful refunds."""
        payment = Payment.objects.select_for_update().select_related('order').get(pk=payment.pk)
        refunded = payment.refunds.filter(status='succeeded').aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
        if refunded <= 0:
            payment.status = 'succeeded'
        elif refunded < payment.amount:
            payment.status = 'partially_refunded'
        else:
            payment.status = 'refunded'
        payment.save(update_fields=['status', 'updated_at'])
        payment.sync_legacy_order()
        return payment

    @staticmethod
    def parse_amount(value):
        try:
            return Decimal(str(value)).quantize(Decimal('0.01'))
        except (InvalidOperation, TypeError, ValueError):
            return None

    @staticmethod
    def payload_hash(payload):
        canonical = json.dumps(payload, sort_keys=True, separators=(',', ':'), default=str)
        return hashlib.sha256(canonical.encode('utf-8')).hexdigest()

    @staticmethod
    def redact_callback_payload(payload):
        """Keep diagnostic structure without persisting phone numbers or customer metadata."""
        callback = payload.get('Body', {}).get('stkCallback', {}) if isinstance(payload, dict) else {}
        metadata_names = []
        for item in callback.get('CallbackMetadata', {}).get('Item', []):
            if isinstance(item, dict) and item.get('Name'):
                metadata_names.append(item['Name'])
        return {
            'Body': {
                'stkCallback': {
                    'MerchantRequestID': callback.get('MerchantRequestID'),
                    'CheckoutRequestID': callback.get('CheckoutRequestID'),
                    'ResultCode': callback.get('ResultCode'),
                    'ResultDesc': str(callback.get('ResultDesc', ''))[:160],
                    'MetadataFields': metadata_names,
                }
            }
        }

    @staticmethod
    @transaction.atomic
    def record_provider_event(payload, checkout_request_id, result_code, receipt_number=''):
        digest = PaymentService.payload_hash(payload)
        event_key = f'mpesa:{checkout_request_id}:{result_code}:{receipt_number or digest[:16]}'
        event, created = PaymentProviderEvent.objects.get_or_create(
            event_key=event_key,
            defaults={
                'provider': 'mpesa',
                'checkout_request_id': checkout_request_id,
                'payload_hash': digest,
                'redacted_payload': PaymentService.redact_callback_payload(payload),
            },
        )
        return event, created
