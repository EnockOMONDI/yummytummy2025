# Generated manually to fix index names with incorrect 'maslove' prefix
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('yummytummy_store', '0010_fix_foreign_key_references'),
    ]

    operations = [
        # Fix index names that still have 'maslove' prefix
        # This is a production-safe operation that only renames indexes
        migrations.RunSQL(
            # Forward SQL - rename indexes to use correct prefix
            """
            -- Drop old indexes with 'maslove' prefix
            DROP INDEX IF EXISTS maslove_sto_code_6da370_idx;
            DROP INDEX IF EXISTS maslove_sto_valid_f_421a10_idx;
            DROP INDEX IF EXISTS maslove_sto_is_acti_36cc54_idx;
            
            -- Create new indexes with correct 'yummytummy_sto' prefix
            CREATE INDEX yummytummy_sto_code_6da370_idx ON yummytummy_store_coupon(code);
            CREATE INDEX yummytummy_sto_valid_f_421a10_idx ON yummytummy_store_coupon(valid_from, valid_to);
            CREATE INDEX yummytummy_sto_is_acti_36cc54_idx ON yummytummy_store_coupon(is_active);
            """,
            # Reverse SQL - restore old index names if needed
            """
            -- Drop new indexes
            DROP INDEX IF EXISTS yummytummy_sto_code_6da370_idx;
            DROP INDEX IF EXISTS yummytummy_sto_valid_f_421a10_idx;
            DROP INDEX IF EXISTS yummytummy_sto_is_acti_36cc54_idx;
            
            -- Restore old indexes
            CREATE INDEX maslove_sto_code_6da370_idx ON yummytummy_store_coupon(code);
            CREATE INDEX maslove_sto_valid_f_421a10_idx ON yummytummy_store_coupon(valid_from, valid_to);
            CREATE INDEX maslove_sto_is_acti_36cc54_idx ON yummytummy_store_coupon(is_active);
            """
        ),
    ]
