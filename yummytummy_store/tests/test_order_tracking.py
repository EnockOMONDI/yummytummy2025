from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils import timezone
from yummytummy_store.models import (
    Category, Product, ProductVariant, Order, OrderItem,
    AutoCreatedAccount, OrderTrackingStatus
)
from yummytummy_store.services import OrderTrackingEmailService, OrderTrackingService


class OrderTrackingTestCase(TestCase):
    def setUp(self):
        """Set up test data"""
        self.client = Client()

        # Create test category
        self.category = Category.objects.create(
            name="Test Category",
            slug="test-category"
        )

        # Create test product
        self.product = Product.objects.create(
            name="Test Honey",
            description="Test honey product",
            price=1000.00,
            is_available=True,
            category=self.category
        )
        
        # Create test variant
        self.variant = ProductVariant.objects.create(
            product=self.product,
            name="500g",
            additional_price=200.00
        )
        
        # Create test user
        self.user = User.objects.create_user(
            username='testuser@example.com',
            email='testuser@example.com',
            password='testpass123',
            first_name='Test',
            last_name='User'
        )

    def test_automatic_account_creation(self):
        """Test that accounts are created automatically during checkout"""
        # Simulate cart session
        session = self.client.session
        session['cart'] = {
            f'{self.product.id}_variant_{self.variant.id}': {
                'product_id': self.product.id,
                'variant_id': self.variant.id,
                'quantity': 2,
                'price': str(self.product.price + self.variant.additional_price),
                'name': f"{self.product.name} - {self.variant.name}",
                'variant_name': self.variant.name,
            }
        }
        session.save()
        
        # Test checkout data
        checkout_data = {
            'first_name': 'New',
            'last_name': 'Customer',
            'email': 'newcustomer@example.com',
            'phone': '+254700000000',
            'address': '123 Test Street',
            'area': 'Test Area',
            'estate': 'Test Estate',
            'building': 'Test Building',
            'landmark': 'Test Landmark',
            'order_notes': 'Test order notes',
        }
        
        # Submit checkout form
        response = self.client.post(reverse('yummytummy_store:checkout'), checkout_data)
        self.assertEqual(response.status_code, 302)  # Redirect to payment
        
        # Submit payment form
        payment_data = {
            'payment_method': 'cash_on_delivery'
        }
        response = self.client.post(reverse('yummytummy_store:payment'), payment_data)
        self.assertEqual(response.status_code, 302)  # Redirect to confirmation
        
        # Check that user was created
        new_user = User.objects.filter(email='newcustomer@example.com').first()
        self.assertIsNotNone(new_user)
        self.assertEqual(new_user.first_name, 'New')
        self.assertEqual(new_user.last_name, 'Customer')
        
        # Check that AutoCreatedAccount was created
        auto_account = AutoCreatedAccount.objects.filter(user=new_user).first()
        self.assertIsNotNone(auto_account)
        self.assertIsNotNone(auto_account.temp_password)
        self.assertIsNotNone(auto_account.first_login_token)
        
        # Check that order was created and linked to user
        order = Order.objects.filter(email='newcustomer@example.com').first()
        self.assertIsNotNone(order)
        self.assertEqual(order.user, new_user)
        self.assertTrue(order.auto_created_account)
        
        # Check that order tracking status was created
        tracking_status = OrderTrackingStatus.objects.filter(order=order).first()
        self.assertIsNotNone(tracking_status)
        self.assertEqual(tracking_status.status, 'order_received')

    def test_existing_user_checkout(self):
        """Test checkout with existing user account"""
        # Simulate cart session
        session = self.client.session
        session['cart'] = {
            f'{self.product.id}_base': {
                'product_id': self.product.id,
                'variant_id': None,
                'quantity': 1,
                'price': str(self.product.price),
                'name': self.product.name,
                'variant_name': None,
            }
        }
        session.save()
        
        # Test checkout data with existing user email
        checkout_data = {
            'first_name': 'Test',
            'last_name': 'User',
            'email': 'testuser@example.com',  # Existing user email
            'phone': '+254700000000',
            'address': '123 Test Street',
            'area': 'Test Area',
            'estate': '',
            'building': '',
            'landmark': '',
            'order_notes': '',
        }
        
        # Submit checkout form
        response = self.client.post(reverse('yummytummy_store:checkout'), checkout_data)
        self.assertEqual(response.status_code, 302)
        
        # Submit payment form
        payment_data = {
            'payment_method': 'mpesa',
            'mpesa_phone': '+254700000000'
        }
        response = self.client.post(reverse('yummytummy_store:payment'), payment_data)
        self.assertEqual(response.status_code, 302)
        
        # Check that no new user was created
        user_count = User.objects.filter(email='testuser@example.com').count()
        self.assertEqual(user_count, 1)
        
        # Check that no AutoCreatedAccount was created for existing user
        auto_account = AutoCreatedAccount.objects.filter(user=self.user).first()
        self.assertIsNone(auto_account)
        
        # Check that order was linked to existing user
        order = Order.objects.filter(email='testuser@example.com').first()
        self.assertIsNotNone(order)
        self.assertEqual(order.user, self.user)
        self.assertFalse(order.auto_created_account)

    def test_order_tracking_service(self):
        """Test order tracking service functionality"""
        # Create test order
        order = Order.objects.create(
            user=self.user,
            first_name='Test',
            last_name='User',
            email='testuser@example.com',
            phone='+254700000000',
            address='123 Test Street',
            payment_method='cash_on_delivery',
            payment_status='processing',
            subtotal_amount=1000.00,
            discount_amount=0.00,
            total_amount=1000.00,
        )
        
        # Test initial tracking status creation
        OrderTrackingService.create_initial_tracking_status(order)
        
        latest_status = order.get_latest_tracking_status()
        self.assertIsNotNone(latest_status)
        self.assertEqual(latest_status.status, 'order_received')

        # Test progress percentage
        progress = OrderTrackingService.get_order_progress_percentage(order)
        self.assertEqual(progress, 10)  # Order received = 10%
        
        # Test tracking history
        history = OrderTrackingService.get_order_tracking_history(order)
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0].status, 'order_received')

    def test_order_tracking_views(self):
        """Test order tracking views require authentication"""
        # Test dashboard requires login
        response = self.client.get(reverse('yummytummy_store:order_tracking_dashboard'))
        self.assertEqual(response.status_code, 302)  # Redirect to login
        
        # Test order detail requires login
        order = Order.objects.create(
            user=self.user,
            first_name='Test',
            last_name='User',
            email='testuser@example.com',
            phone='+254700000000',
            address='123 Test Street',
            payment_method='cash_on_delivery',
            payment_status='processing',
            subtotal_amount=1000.00,
            discount_amount=0.00,
            total_amount=1000.00,
        )
        
        response = self.client.get(
            reverse('yummytummy_store:order_detail_tracking', args=[order.id])
        )
        self.assertEqual(response.status_code, 302)  # Redirect to login
        
        # Login and test access
        self.client.login(username='testuser@example.com', password='testpass123')
        
        response = self.client.get(reverse('yummytummy_store:order_tracking_dashboard'))
        self.assertEqual(response.status_code, 200)
        
        response = self.client.get(
            reverse('yummytummy_store:order_detail_tracking', args=[order.id])
        )
        self.assertEqual(response.status_code, 200)

    def test_first_time_login_token(self):
        """Test first-time login with token"""
        # Create test order for auto account
        order = Order.objects.create(
            user=self.user,
            first_name='Test',
            last_name='User',
            email='testuser@example.com',
            phone='+254700000000',
            address='123 Test Street',
            payment_method='cash_on_delivery',
            payment_status='processing',
            subtotal_amount=1000.00,
            discount_amount=0.00,
            total_amount=1000.00,
        )

        # Create auto-created account
        auto_account = AutoCreatedAccount.objects.create(
            user=self.user,
            created_during_order=order,
            first_login_token='test-token-123',
            token_expires=timezone.now() + timezone.timedelta(days=7),  # Valid token
            first_login_completed=False
        )
        
        # Test first-time login
        response = self.client.get(
            reverse('yummytummy_store:first_time_login', args=['test-token-123'])
        )
        self.assertEqual(response.status_code, 302)  # Redirect to dashboard
        
        # Check that first login was marked as completed
        auto_account.refresh_from_db()
        self.assertTrue(auto_account.first_login_completed)
        
        # Test invalid token
        response = self.client.get(
            reverse('yummytummy_store:first_time_login', args=['invalid-token'])
        )
        self.assertEqual(response.status_code, 302)  # Redirect to home with error
