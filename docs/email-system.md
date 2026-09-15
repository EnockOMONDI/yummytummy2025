# YummyTummy Email System

YummyTummy uses the Novustell-style production email setup: Django email APIs routed through Resend via `django-anymail`.

## Production Provider

- Backend: `anymail.backends.resend.EmailBackend`
- Secret: `RESEND_API_KEY`
- Default sender: `YummyTummy <info@yummytummy.co.ke>`
- Admin/support inbox: `info@yummytummy.co.ke`
- Order operations inbox: `orders@yummytummy.co.ke`

## Render Environment Variables

Set these in Render:

```text
EMAIL_BACKEND=anymail.backends.resend.EmailBackend
RESEND_API_KEY=<your Resend API key>
DEFAULT_FROM_EMAIL=YummyTummy <info@yummytummy.co.ke>
ADMIN_EMAIL=info@yummytummy.co.ke
ORDERS_EMAIL=orders@yummytummy.co.ke
```

`EMAIL_HOST`, `EMAIL_HOST_USER`, and `EMAIL_HOST_PASSWORD` are no longer required for production unless you intentionally switch back to SMTP.

## Email Flow Map

| Flow | Trigger | Recipient | Template |
| --- | --- | --- | --- |
| Magic login | User requests passwordless sign-in | Customer/user email | `magic_login.html`, `magic_login.txt` |
| Regular order confirmation | Paid/confirmed customer order without auto-created account | Customer order email | `order_confirmation_guest.html` or `order_confirmation_user.html` |
| Payment confirmation with account | Paid order that created an account | Customer account email | `payment_confirmation_with_account.html` |
| Payment failure | Failed M-Pesa callback/payment attempt | Customer order email | `payment_failed_notification.html`, `payment_failed_notification.txt` |
| Order status update | Admin/sales status update | Customer order email | `order_status_update.html` |
| Recipe purchase confirmation | Paid digital recipe purchase | Customer order email | `recipe_purchase_confirmation.html`, `recipe_purchase_confirmation.txt` |
| Offline order alert | Sales team creates offline order | `orders@yummytummy.co.ke` | `business_offline_order_notification.html`, `business_offline_order_notification.txt` |

## Queue And Retry

Customer payment and tracking messages still use `NotificationOutbox`. Immediate delivery is attempted after database commit. Failed or queued records can be retried from admin or with:

```bash
python manage.py process_notifications
```

For production reliability, schedule that command in Render Cron or another scheduler.
