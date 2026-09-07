"""
Tests for database constraints and foreign key integrity
"""
from django.test import TestCase
from django.db import connection
from yummytummy_store.models import Category, Product, ProductVariant


class DatabaseConstraintTests(TestCase):
    """Test database constraints and foreign key integrity"""
    
    def setUp(self):
        """Set up test data"""
        self.category = Category.objects.create(
            name="Test Category",
            description="Test description",
            slug="test-category"
        )
        
        self.product = Product.objects.create(
            category=self.category,
            name="Test Product",
            description="Test product description",
            price=25.00,
            size="400g",
            slug="test-product"
        )
    
    def application_constraints(self):
        with connection.cursor() as cursor:
            return {
                table: connection.introspection.get_constraints(cursor, table)
                for table in connection.introspection.table_names(cursor)
                if table.startswith('yummytummy_store_')
            }

    def test_foreign_key_constraints_exist(self):
        constraints = self.application_constraints()['yummytummy_store_product']
        foreign_keys = [value for value in constraints.values() if value.get('foreign_key')]
        self.assertEqual(len(foreign_keys), 1)
        self.assertEqual(foreign_keys[0]['foreign_key'], ('yummytummy_store_category', 'id'))
        self.assertEqual(foreign_keys[0]['columns'], ['category_id'])

    def test_no_maslove_references_in_constraints(self):
        for table, constraints in self.application_constraints().items():
            for value in constraints.values():
                if value.get('foreign_key'):
                    self.assertNotIn('maslove', value['foreign_key'][0].lower(), table)

    def test_no_maslove_indexes_after_migration(self):
        for constraints in self.application_constraints().values():
            for name, value in constraints.items():
                if value.get('index'):
                    self.assertNotIn('maslove', name.lower())

    def test_correct_yummytummy_indexes_exist(self):
        names = [
            name for constraints in self.application_constraints().values()
            for name, value in constraints.items() if value.get('index')
        ]
        self.assertTrue(any(name.startswith('yummytummy_sto') for name in names))
    
    def test_data_integrity_after_constraint_fixes(self):
        """Test that data integrity is maintained after constraint fixes"""
        # Test creating related objects
        variant = ProductVariant.objects.create(
            product=self.product,
            name="Test Variant",
            additional_price=5.00
        )

        # Verify relationships work for variant
        self.assertEqual(variant.product, self.product)
        self.assertEqual(self.product.category, self.category)

        # Test that we can query related objects
        variants = self.product.variants.all()
        self.assertEqual(len(variants), 1)
        self.assertEqual(variants[0], variant)
    
    def test_cascade_deletes_work(self):
        """Test that cascade deletes work properly with fixed constraints"""
        # Create related objects
        variant = ProductVariant.objects.create(
            product=self.product,
            name="Test Variant",
            additional_price=5.00
        )

        # Verify variant was created
        self.assertEqual(variant.product, self.product)

        # Delete product should cascade to variant
        product_id = self.product.id
        self.product.delete()

        # Variant should be deleted
        self.assertFalse(ProductVariant.objects.filter(product_id=product_id).exists())
    
    def test_database_schema_consistency(self):
        """Test overall database schema consistency"""
        with connection.cursor() as cursor:
            # Check that all expected tables exist
            tables = connection.introspection.table_names(cursor)
            
            expected_tables = [
                'yummytummy_store_category',
                'yummytummy_store_product', 
                'yummytummy_store_productvariant',
                'yummytummy_store_ingredient',
                'yummytummy_store_productingredient',
                'yummytummy_store_order',
                'yummytummy_store_orderitem',
                'yummytummy_store_coupon',
                'yummytummy_store_couponusage'
                , 'yummytummy_store_payment'
                , 'yummytummy_store_paymentattempt'
                , 'yummytummy_store_paymentproviderevent'
                , 'yummytummy_store_refund'
                , 'yummytummy_store_notificationoutbox'
            ]
            
            for expected_table in expected_tables:
                self.assertIn(expected_table, tables, f"Expected table {expected_table} not found")


class DatabaseMigrationTests(TestCase):
    """Test database migration operations"""
    
    def test_current_migration_leaf(self):
        """Check the expected schema migration is the current leaf."""
        from django.db.migrations.loader import MigrationLoader

        loader = MigrationLoader(connection)
        self.assertIn(
            ('yummytummy_store', '0011_alter_order_options_refund_completed_at'),
            loader.graph.leaf_nodes('yummytummy_store'),
        )
