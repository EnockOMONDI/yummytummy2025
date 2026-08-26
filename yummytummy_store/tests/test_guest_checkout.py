from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from yummytummy_store.models import AutoCreatedAccount, Category, Order, Product


class GuestCheckoutTestCase(TestCase):
    def setUp(self):
        self.category = Category.objects.create(
            name='Nut Butter',
            slug='nut-butter',
        )
        self.product = Product.objects.create(
            name='Peanut Butter',
            slug='peanut-butter',
            description='Smooth peanut butter',
            price=Decimal('450.00'),
            category=self.category,
            is_available=True,
        )

    def add_product_to_session_cart(self):
        session = self.client.session
        session['cart'] = {
            f'{self.product.id}_base': {
                'product_id': self.product.id,
                'variant_id': None,
                'quantity': 1,
                'price': str(self.product.price),
                'name': self.product.name,
                'variant_name': None,
                'type': 'product',
            }
        }
        session.save()

    def submit_checkout(self, email='guest@example.com'):
        return self.client.post(reverse('yummytummy_store:checkout'), {
            'first_name': 'Guest',
            'last_name': 'Customer',
            'email': email,
            'phone': '0712345678',
            'address': '123 Test Street',
            'area': 'Westlands',
            'estate': '',
            'building': '',
            'landmark': '',
            'order_notes': '',
        })

    def submit_bank_payment(self):
        return self.client.post(reverse('yummytummy_store:payment'), {
            'payment_method': 'bank',
            'terms_accepted': 'on',
        })

    def test_anonymous_product_checkout_creates_guest_order(self):
        self.add_product_to_session_cart()

        response = self.submit_checkout()
        self.assertRedirects(response, reverse('yummytummy_store:payment'))

        response = self.submit_bank_payment()
        self.assertRedirects(response, reverse('yummytummy_store:order_confirmation'))

        order = Order.objects.get(email='guest@example.com')
        self.assertIsNone(order.user)
        self.assertFalse(order.auto_created_account)
        self.assertFalse(User.objects.filter(email='guest@example.com').exists())
        self.assertFalse(AutoCreatedAccount.objects.exists())

    def test_authenticated_product_checkout_links_to_logged_in_user(self):
        user = User.objects.create_user(
            username='buyer@example.com',
            email='buyer@example.com',
            password='testpass123',
            first_name='Buyer',
            last_name='Person',
        )
        self.client.login(username='buyer@example.com', password='testpass123')
        self.add_product_to_session_cart()

        response = self.submit_checkout(email='buyer@example.com')
        self.assertRedirects(response, reverse('yummytummy_store:payment'))

        response = self.submit_bank_payment()
        self.assertRedirects(response, reverse('yummytummy_store:order_confirmation'))

        order = Order.objects.get(email='buyer@example.com')
        self.assertEqual(order.user, user)
        self.assertFalse(order.auto_created_account)
        self.assertFalse(AutoCreatedAccount.objects.exists())
