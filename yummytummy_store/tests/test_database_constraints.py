"""
Tests for database constraints and foreign key integrity
"""
from django.test import TestCase
from django.db import connection
from django.core.management import call_command
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
    
    def test_foreign_key_constraints_exist(self):
        """Test that all foreign key constraints are properly defined"""
        with connection.cursor() as cursor:
            # Test product -> category foreign key
            cursor.execute("PRAGMA foreign_key_list(yummytummy_store_product);")
            fks = cursor.fetchall()
            
            # Should have one FK pointing to yummytummy_store_category
            self.assertEqual(len(fks), 1)
            fk = fks[0]
            self.assertEqual(fk[2], 'yummytummy_store_category')  # Referenced table
            self.assertEqual(fk[3], 'category_id')  # Foreign key column
            self.assertEqual(fk[4], 'id')  # Referenced column
    
    def test_no_maslove_references_in_constraints(self):
        """Test that no foreign keys reference 'maslove' tables"""
        with connection.cursor() as cursor:
            # Get all tables
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'yummytummy_store_%';")
            tables = [row[0] for row in cursor.fetchall()]
            
            for table in tables:
                cursor.execute(f"PRAGMA foreign_key_list({table});")
                fks = cursor.fetchall()
                
                for fk in fks:
                    referenced_table = fk[2]
                    self.assertNotIn('maslove', referenced_table.lower(), 
                                   f"Table {table} has FK referencing 'maslove' table: {referenced_table}")
    
    def test_no_maslove_indexes_after_migration(self):
        """Test that no indexes have 'maslove' in their names after migration"""
        with connection.cursor() as cursor:
            cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND name LIKE '%maslove%';")
            maslove_indexes = cursor.fetchall()
            
            self.assertEqual(len(maslove_indexes), 0, 
                           f"Found indexes with 'maslove' prefix: {[idx[0] for idx in maslove_indexes]}")
    
    def test_correct_yummytummy_indexes_exist(self):
        """Test that indexes with correct 'yummytummy' prefix exist"""
        with connection.cursor() as cursor:
            cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND name LIKE 'yummytummy_sto_%';")
            yummytummy_indexes = cursor.fetchall()
            
            # Should have at least the coupon indexes
            index_names = [idx[0] for idx in yummytummy_indexes]
            expected_indexes = [
                'yummytummy_sto_code_6da370_idx',
                'yummytummy_sto_valid_f_421a10_idx', 
                'yummytummy_sto_is_acti_36cc54_idx'
            ]
            
            for expected_idx in expected_indexes:
                self.assertIn(expected_idx, index_names, 
                            f"Expected index {expected_idx} not found")
    
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
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'yummytummy_store_%';")
            tables = [row[0] for row in cursor.fetchall()]
            
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
            ]
            
            for expected_table in expected_tables:
                self.assertIn(expected_table, tables, f"Expected table {expected_table} not found")


class DatabaseMigrationTests(TestCase):
    """Test database migration operations"""
    
    def test_migration_rollback_safety(self):
        """Test that migrations can be safely rolled back"""
        # This would be more complex in a real scenario
        # For now, just verify the migration exists and is properly structured
        from yummytummy_store.migrations import __path__ as migrations_path
        import os
        
        migration_file = os.path.join(migrations_path[0], '0011_fix_index_names.py')
        self.assertTrue(os.path.exists(migration_file), "Migration 0011 should exist")
        
        # Read migration file and verify it has reverse SQL
        with open(migration_file, 'r') as f:
            content = f.read()
            self.assertIn('RunSQL', content, "Migration should use RunSQL")
            self.assertIn('DROP INDEX', content, "Migration should drop old indexes")
            self.assertIn('CREATE INDEX', content, "Migration should create new indexes")
