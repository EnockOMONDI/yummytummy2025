"""
Integration tests for complete cart variant user journey.
Tests end-to-end functionality from product selection to order completion.
"""

from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from decimal import Decimal
from yummytummy_store.models import Category, Product, ProductVariant, Order, OrderItem, Coupon


class CartVariantIntegrationTestCase(TestCase):
    """Integration test case for complete cart variant workflow"""
    
    def setUp(self):
        """Set up test data"""
        self.client = Client()
        
        # Create test category
        self.category = Category.objects.create(
            name="Premium Honey",
            slug="premium-honey"
        )
        
        # Create test products
        self.product1 = Product.objects.create(
            name="Wildflower Honey",
            slug="wildflower-honey",
            description="Pure wildflower honey",
            price=Decimal('1000.00'),
            category=self.category,
            is_available=True,
            is_featured=True
        )
        
        self.product2 = Product.objects.create(
            name="Acacia Honey",
            slug="acacia-honey",
            description="Premium acacia honey",
            price=Decimal('1500.00'),
            category=self.category,
            is_available=True
        )
        
        # Create variants for product1
        self.variant1_250g = ProductVariant.objects.create(
            product=self.product1,
            name="250g",
            additional_price=Decimal('0.00')
        )
        
        self.variant1_500g = ProductVariant.objects.create(
            product=self.product1,
            name="500g",
            additional_price=Decimal('300.00')
        )
        
        # Create variants for product2
        self.variant2_400g = ProductVariant.objects.create(
            product=self.product2,
            name="400g",
            additional_price=Decimal('0.00')
        )
        
        self.variant2_800g = ProductVariant.objects.create(
            product=self.product2,
            name="800g",
            additional_price=Decimal('400.00')
        )
        
        # Create test user
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        # Create test coupon
        self.coupon = Coupon.objects.create(
            code='TEST10',
            discount_type='percentage',
            discount_value=Decimal('10.00'),
            min_order_amount=Decimal('2000.00'),
            usage_limit=100,
            per_customer_limit=5,
            is_active=True
        )

    def test_complete_user_journey_with_variants(self):
        """Test complete user journey from product selection to order completion"""
        
        # Step 1: Add base product to cart
        response = self.client.post(reverse('yummytummy_store:cart_add', args=[self.product1.id]), {
            'quantity': 1,
            'update': False,
            'selected_variant': 'base'
        })
        self.assertEqual(response.status_code, 302)
        
        # Step 2: Add variant of same product
        response = self.client.post(reverse('yummytummy_store:cart_add', args=[self.product1.id]), {
            'quantity': 2,
            'update': False,
            'selected_variant': str(self.variant1_500g.id)
        })
        self.assertEqual(response.status_code, 302)
        
        # Step 3: Add variant of different product
        response = self.client.post(reverse('yummytummy_store:cart_add', args=[self.product2.id]), {
            'quantity': 1,
            'update': False,
            'selected_variant': str(self.variant2_800g.id)
        })
        self.assertEqual(response.status_code, 302)
        
        # Step 4: View cart and verify contents
        response = self.client.get(reverse('yummytummy_store:cart_detail'))
        self.assertEqual(response.status_code, 200)
        
        cart_items = response.context['cart_items']
        self.assertEqual(len(cart_items), 3)  # 3 different cart items
        
        # Verify cart totals
        subtotal = response.context['subtotal']
        expected_subtotal = (
            self.product1.price +  # Base product1
            (self.product1.price + self.variant1_500g.additional_price) * 2 +  # Variant 500g x2
            (self.product2.price + self.variant2_800g.additional_price)  # Variant 800g
        )
        self.assertEqual(subtotal, expected_subtotal)
        
        # Step 5: Update quantity of specific variant
        variant_key = f"{self.product1.id}_variant_{self.variant1_500g.id}"
        response = self.client.post(reverse('yummytummy_store:cart_update', args=[variant_key]), {
            'quantity': 3,
            'update': True
        })
        self.assertEqual(response.status_code, 302)
        
        # Step 6: Remove specific variant
        base_key = f"{self.product1.id}_base"
        response = self.client.get(reverse('yummytummy_store:cart_remove_item', args=[base_key]))
        self.assertEqual(response.status_code, 302)
        
        # Step 7: Verify cart after updates
        response = self.client.get(reverse('yummytummy_store:cart_detail'))
        cart_items = response.context['cart_items']
        self.assertEqual(len(cart_items), 2)  # Should have 2 items left
        
        # Step 8: Apply coupon
        response = self.client.post(reverse('yummytummy_store:coupon_apply'), {
            'code': 'TEST10'
        })
        self.assertEqual(response.status_code, 302)
        
        # Step 9: Proceed to checkout
        response = self.client.get(reverse('yummytummy_store:checkout'))
        self.assertEqual(response.status_code, 200)
        
        # Verify checkout displays variant information
        cart_items = response.context['cart_items']
        for item in cart_items:
            self.assertIn('variant_name', item)
            if item['variant_name']:
                self.assertIn('variant_name', item)

    def test_mixed_cart_checkout_process(self):
        """Test checkout process with mixed cart contents (base + variants)"""
        
        # Add mixed items to cart
        self.client.post(reverse('yummytummy_store:cart_add', args=[self.product1.id]), {
            'quantity': 1,
            'update': False,
            'selected_variant': 'base'
        })
        
        self.client.post(reverse('yummytummy_store:cart_add', args=[self.product2.id]), {
            'quantity': 1,
            'update': False,
            'selected_variant': str(self.variant2_400g.id)
        })
        
        # Proceed to checkout
        response = self.client.get(reverse('yummytummy_store:checkout'))
        self.assertEqual(response.status_code, 200)
        
        # Submit checkout form
        checkout_data = {
            'first_name': 'John',
            'last_name': 'Doe',
            'email': 'john@example.com',
            'phone': '0712345678',
            'address': '123 Test Street',
            'area': 'Test Area',
            'estate': 'Test Estate',
            'building': 'Building 1',
            'landmark': 'Near Test Mall',
            'order_notes': 'Test order'
        }
        
        response = self.client.post(reverse('yummytummy_store:checkout'), checkout_data)
        self.assertEqual(response.status_code, 302)  # Redirect to payment
        
        # Verify checkout data in session
        session = self.client.session
        self.assertIn('checkout_data', session)

    def test_cart_persistence_across_sessions(self):
        """Test cart persistence across browser sessions"""
        
        # Add items to cart
        self.client.post(reverse('yummytummy_store:cart_add', args=[self.product1.id]), {
            'quantity': 1,
            'update': False,
            'selected_variant': str(self.variant1_500g.id)
        })
        
        # Get current session cart
        session = self.client.session
        original_cart = session.get('cart', {})
        
        # Simulate new session by creating new client
        new_client = Client()
        
        # Manually set the session cart (simulating persistence)
        new_session = new_client.session
        new_session['cart'] = original_cart
        new_session.save()
        
        # Verify cart contents in new session
        response = new_client.get(reverse('yummytummy_store:cart_detail'))
        self.assertEqual(response.status_code, 200)
        
        cart_items = response.context['cart_items']
        self.assertEqual(len(cart_items), 1)

    def test_variant_edge_cases(self):
        """Test edge cases in variant handling"""
        
        # Test adding same variant multiple times
        for _ in range(3):
            self.client.post(reverse('yummytummy_store:cart_add', args=[self.product1.id]), {
                'quantity': 1,
                'update': False,
                'selected_variant': str(self.variant1_500g.id)
            })
        
        # Should accumulate quantity, not create multiple entries
        session = self.client.session
        cart = session.get('cart', {})
        
        variant_key = f"{self.product1.id}_variant_{self.variant1_500g.id}"
        self.assertEqual(cart[variant_key]['quantity'], 3)
        
        # Test updating with quantity 0 (should not be allowed by form validation)
        response = self.client.post(reverse('yummytummy_store:cart_update', args=[variant_key]), {
            'quantity': 0,
            'update': True
        })
        # Should redirect back to cart (form validation should prevent this)
        self.assertEqual(response.status_code, 302)

    def test_product_availability_changes(self):
        """Test behavior when product availability changes after adding to cart"""
        
        # Add product to cart
        self.client.post(reverse('yummytummy_store:cart_add', args=[self.product1.id]), {
            'quantity': 1,
            'update': False,
            'selected_variant': str(self.variant1_500g.id)
        })
        
        # Make product unavailable
        self.product1.is_available = False
        self.product1.save()
        
        # Cart should still display the item (business decision)
        response = self.client.get(reverse('yummytummy_store:cart_detail'))
        self.assertEqual(response.status_code, 200)
        
        cart_items = response.context['cart_items']
        self.assertEqual(len(cart_items), 1)

    def test_large_cart_performance(self):
        """Test cart performance with many variants"""
        
        # Add many different variants to cart
        variants = [self.variant1_250g, self.variant1_500g, self.variant2_400g, self.variant2_800g]
        
        for i, variant in enumerate(variants):
            self.client.post(reverse('yummytummy_store:cart_add', args=[variant.product.id]), {
                'quantity': i + 1,
                'update': False,
                'selected_variant': str(variant.id)
            })
        
        # Test cart detail view performance
        response = self.client.get(reverse('yummytummy_store:cart_detail'))
        self.assertEqual(response.status_code, 200)
        
        cart_items = response.context['cart_items']
        self.assertEqual(len(cart_items), len(variants))
        
        # Verify total calculation is correct
        expected_total = sum(
            (variant.product.price + variant.additional_price) * (i + 1)
            for i, variant in enumerate(variants)
        )
        self.assertEqual(response.context['subtotal'], expected_total)

    def test_concurrent_cart_operations(self):
        """Test concurrent cart operations (simulated)"""
        
        # Add item to cart
        self.client.post(reverse('yummytummy_store:cart_add', args=[self.product1.id]), {
            'quantity': 1,
            'update': False,
            'selected_variant': str(self.variant1_500g.id)
        })
        
        # Simulate concurrent update operations
        variant_key = f"{self.product1.id}_variant_{self.variant1_500g.id}"
        
        # Multiple rapid updates
        for quantity in [2, 3, 4, 5]:
            response = self.client.post(reverse('yummytummy_store:cart_update', args=[variant_key]), {
                'quantity': quantity,
                'update': True
            })
            self.assertEqual(response.status_code, 302)
        
        # Verify final state
        session = self.client.session
        cart = session.get('cart', {})
        self.assertEqual(cart[variant_key]['quantity'], 5)

    def test_cart_error_handling(self):
        """Test cart error handling scenarios"""
        
        # Test updating non-existent cart item
        fake_key = "999_variant_999"
        response = self.client.post(reverse('yummytummy_store:cart_update', args=[fake_key]), {
            'quantity': 1,
            'update': True
        })
        self.assertEqual(response.status_code, 302)  # Should redirect gracefully
        
        # Test removing non-existent cart item
        response = self.client.get(reverse('yummytummy_store:cart_remove_item', args=[fake_key]))
        self.assertEqual(response.status_code, 302)  # Should redirect gracefully
