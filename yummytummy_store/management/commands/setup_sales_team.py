from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission, User
from django.contrib.contenttypes.models import ContentType
from yummytummy_store.models import Order

class Command(BaseCommand):
    help = 'Set up Sales Team group with appropriate permissions'

    def handle(self, *args, **options):
        # Create Sales Team group
        sales_group, created = Group.objects.get_or_create(name='Sales Team')
        
        if created:
            self.stdout.write(
                self.style.SUCCESS('Created Sales Team group')
            )
        else:
            self.stdout.write(
                self.style.WARNING('Sales Team group already exists')
            )

        # Get Order content type
        order_content_type = ContentType.objects.get_for_model(Order)
        
        # Get or create add_order permission
        add_order_permission, created = Permission.objects.get_or_create(
            codename='add_order',
            name='Can add order',
            content_type=order_content_type,
        )
        
        # Add permission to Sales Team group
        sales_group.permissions.add(add_order_permission)
        
        self.stdout.write(
            self.style.SUCCESS('Added add_order permission to Sales Team group')
        )
        
        # Create a sample sales team user (optional)
        sales_user, created = User.objects.get_or_create(
            username='sales_demo',
            defaults={
                'email': 'sales@yummytummy.com',
                'first_name': 'Sales',
                'last_name': 'Demo',
                'is_staff': True,  # Required to access admin-like interfaces
            }
        )
        
        if created:
            sales_user.set_password('sales123')  # Change this in production
            sales_user.save()
            sales_user.groups.add(sales_group)
            
            self.stdout.write(
                self.style.SUCCESS('Created demo sales user: sales_demo / sales123')
            )
        else:
            # Ensure existing user is in sales group
            sales_user.groups.add(sales_group)
            self.stdout.write(
                self.style.WARNING('Demo sales user already exists')
            )
        
        self.stdout.write(
            self.style.SUCCESS('Sales Team setup completed successfully!')
        )
