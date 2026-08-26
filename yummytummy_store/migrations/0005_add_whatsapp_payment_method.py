from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('yummytummy_store', '0004_recipecategory_recipe_recipepurchase_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='order',
            name='payment_method',
            field=models.CharField(
                choices=[
                    ('mpesa', 'M-Pesa'),
                    ('card', 'Credit/Debit Card'),
                    ('bank', 'Bank Transfer'),
                    ('whatsapp', 'WhatsApp Order'),
                ],
                default='mpesa',
                max_length=20,
            ),
        ),
    ]
