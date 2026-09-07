import logging
from datetime import timedelta

from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from .models import NotificationOutbox, RecipePurchase

logger = logging.getLogger(__name__)


class NotificationService:
    """Durable notification queue with synchronous delivery as a safe fallback."""

    @staticmethod
    def enqueue_tracking_update(tracking_status):
        if not tracking_status.order.email:
            return None
        outbox = NotificationOutbox.objects.create(
            event_type='tracking_status_update',
            order=tracking_status.order,
            tracking_status=tracking_status,
            recipient=tracking_status.order.email,
        )
        transaction.on_commit(lambda: NotificationService.process(outbox.pk))
        return outbox

    @staticmethod
    def enqueue_payment_result(order, succeeded, failure_reason=''):
        if not order.email:
            return None
        outbox = NotificationOutbox.objects.create(
            event_type='payment_confirmation' if succeeded else 'payment_failed',
            order=order,
            recipient=order.email,
            payload={'failure_reason': str(failure_reason)[:160]} if failure_reason else {},
        )
        transaction.on_commit(lambda: NotificationService.process(outbox.pk))
        return outbox

    @staticmethod
    def process(outbox_id):
        from .services import OrderTrackingEmailService

        stale_before = timezone.now() - timedelta(minutes=15)
        with transaction.atomic():
            outbox = (
                NotificationOutbox.objects.select_for_update(of=('self',))
                .select_related('order', 'tracking_status')
                .filter(pk=outbox_id)
                .first()
            )
            if not outbox or outbox.status == 'sent':
                return False
            if (
                outbox.status == 'processing'
                and outbox.processed_at
                and outbox.processed_at > stale_before
            ):
                return False

            outbox.status = 'processing'
            outbox.attempts += 1
            outbox.processed_at = timezone.now()
            outbox.save(update_fields=['status', 'attempts', 'processed_at'])

        try:
            if outbox.event_type == 'tracking_status_update' and outbox.tracking_status:
                sent = OrderTrackingEmailService.send_status_update_email(
                    outbox.order,
                    outbox.tracking_status,
                )
            elif outbox.event_type == 'payment_confirmation':
                if outbox.order.auto_created_account:
                    sent = OrderTrackingEmailService.send_payment_confirmation_email(outbox.order)
                else:
                    sent = OrderTrackingEmailService.send_regular_order_confirmation(outbox.order)
                recipe_ids = outbox.order.recipe_items.values_list('recipe_id', flat=True)
                recipe_purchases = RecipePurchase.objects.filter(
                    user_id=outbox.order.user_id,
                    recipe_id__in=recipe_ids,
                ).select_related('recipe')
                if outbox.order.user_id and recipe_purchases.exists():
                    sent = (
                        OrderTrackingEmailService.send_recipe_purchase_confirmation(
                            outbox.order,
                            recipe_purchases,
                        )
                        and sent
                    )
            elif outbox.event_type == 'payment_failed':
                sent = OrderTrackingEmailService.send_payment_failed_notification(
                    outbox.order,
                    failure_reason=outbox.payload.get('failure_reason'),
                )
            else:
                raise ValueError(f'Unsupported notification type: {outbox.event_type}')

            if not sent:
                raise RuntimeError('Email backend did not confirm delivery.')

            outbox.status = 'sent'
            outbox.last_error = ''
            outbox.processed_at = timezone.now()
            outbox.save(update_fields=['status', 'last_error', 'processed_at'])
            return True
        except Exception as exc:
            logger.warning('Notification %s failed: %s', outbox.pk, exc.__class__.__name__)
            outbox.status = 'failed'
            outbox.last_error = str(exc)[:255]
            outbox.processed_at = timezone.now()
            outbox.save(update_fields=['status', 'last_error', 'processed_at'])
            return False

    @staticmethod
    def process_pending(limit=50):
        stale_before = timezone.now() - timedelta(minutes=15)
        ids = list(
            NotificationOutbox.objects.filter(
                Q(status__in=['queued', 'failed'])
                | Q(status='processing', processed_at__lt=stale_before)
                | Q(status='processing', processed_at__isnull=True)
            )
            .order_by('created_at')
            .values_list('pk', flat=True)[:limit]
        )
        return sum(1 for outbox_id in ids if NotificationService.process(outbox_id))
