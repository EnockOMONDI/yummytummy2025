"""
Django management command to diagnose database constraint issues
"""
from django.core.management.base import BaseCommand
from django.db import connection
import sqlite3


class Command(BaseCommand):
    help = 'Diagnose database constraint and foreign key issues'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('=== Database Constraint Diagnosis ===\n'))
        
        # Check all tables
        with connection.cursor() as cursor:
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'yummytummy_store_%';")
            tables = [row[0] for row in cursor.fetchall()]
            
            self.stdout.write(f"Found {len(tables)} YummyTummy tables:")
            for table in tables:
                self.stdout.write(f"  - {table}")
            
            self.stdout.write("\n=== Foreign Key Constraints ===")
            for table in tables:
                cursor.execute(f"PRAGMA foreign_key_list({table});")
                fks = cursor.fetchall()
                if fks:
                    self.stdout.write(f"\n{table}:")
                    for fk in fks:
                        self.stdout.write(f"  FK: {fk[3]} -> {fk[2]}.{fk[4]}")
                        # Check if referenced table exists
                        cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{fk[2]}';")
                        if not cursor.fetchone():
                            self.stdout.write(self.style.ERROR(f"    ERROR: Referenced table '{fk[2]}' does not exist!"))
            
            self.stdout.write("\n=== Index Names with 'maslove' ===")
            cursor.execute("SELECT name, tbl_name FROM sqlite_master WHERE type='index' AND name LIKE '%maslove%';")
            indexes = cursor.fetchall()
            if indexes:
                for idx_name, table_name in indexes:
                    self.stdout.write(f"  {table_name}: {idx_name}")
            else:
                self.stdout.write("  No 'maslove' indexes found")
            
            self.stdout.write("\n=== Migration State ===")
            cursor.execute("SELECT app, name FROM django_migrations WHERE app='yummytummy_store' ORDER BY id;")
            migrations = cursor.fetchall()
            self.stdout.write("Applied migrations:")
            for app, name in migrations:
                self.stdout.write(f"  {app}.{name}")
        
        self.stdout.write(self.style.SUCCESS('\n=== Diagnosis Complete ==='))
