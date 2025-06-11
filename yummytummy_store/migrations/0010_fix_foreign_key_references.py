# Generated manually to fix foreign key references
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('yummytummy_store', '0009_migrate_images_to_legacy'),
    ]

    operations = [
        # This migration fixes foreign key references that were pointing to the old app name
        migrations.RunSQL(
            # Forward SQL - disable foreign keys, recreate table, re-enable
            """
            PRAGMA foreign_keys=OFF;

            CREATE TABLE yummytummy_store_product_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name VARCHAR(200) NOT NULL,
                description TEXT NOT NULL,
                price DECIMAL NOT NULL,
                size VARCHAR(50) NOT NULL,
                slug VARCHAR(200) NOT NULL UNIQUE,
                is_available BOOLEAN NOT NULL,
                created DATETIME NOT NULL,
                updated DATETIME NOT NULL,
                category_id INTEGER NOT NULL REFERENCES yummytummy_store_category(id) DEFERRABLE INITIALLY DEFERRED,
                feature_type VARCHAR(20) NOT NULL,
                is_featured BOOLEAN NOT NULL,
                legacy_image VARCHAR(100),
                image TEXT NOT NULL
            );

            INSERT INTO yummytummy_store_product_new
            SELECT id, name, description, price, size, slug, is_available, created, updated, category_id, feature_type, is_featured, legacy_image, image
            FROM yummytummy_store_product;

            DROP TABLE yummytummy_store_product;

            ALTER TABLE yummytummy_store_product_new
            RENAME TO yummytummy_store_product;

            CREATE INDEX yummytummy_store_product_category_id_idx
            ON yummytummy_store_product(category_id);

            CREATE INDEX yummytummy_store_product_id_slug_idx
            ON yummytummy_store_product(id, slug);

            CREATE INDEX yummytummy_store_product_name_idx
            ON yummytummy_store_product(name);

            CREATE INDEX yummytummy_store_product_created_idx
            ON yummytummy_store_product(created DESC);

            PRAGMA foreign_keys=ON;
            """,
            # Reverse SQL - not implemented as this is a one-way fix
            migrations.RunSQL.noop
        ),
    ]
