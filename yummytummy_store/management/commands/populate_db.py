from django.core.management.base import BaseCommand
from django.utils.text import slugify
from yummytummy_store.models import Category, Product, Ingredient, ProductIngredient, ProductVariant

class Command(BaseCommand):
    help = 'Populate the database with initial data'

    def handle(self, *args, **kwargs):
        self.stdout.write('Creating initial data...')

        # Create categories
        nut_butters = Category.objects.create(
            name='Nut Butters',
            description='Delicious spreads made from various nuts',
            slug='nut-butters'
        )

        nut_mixes = Category.objects.create(
            name='Nut Mixes',
            description='Mixes of different nuts and dried fruits',
            slug='nut-mixes'
        )

        # Create ingredients
        peanuts = Ingredient.objects.create(
            name='Peanuts',
            description='Roasted peanuts from selected farms'
        )

        cashews = Ingredient.objects.create(
            name='Cashews',
            description='Premium cashews with rich flavor'
        )

        honey = Ingredient.objects.create(
            name='Natural Honey',
            description='Pure, natural honey from local beekeepers'
        )

        # Create products
        peanut_butter = Product.objects.create(
            category=nut_butters,
            name='Crunchy Peanut Butter',
            description='Our classic crunchy peanut butter made from 100% peanuts with no additives or preservatives. Perfect for spreading on toast, adding to smoothies, or using in recipes.',
            price=23.00,
            size='400g',
            slug='crunchy-peanut-butter',
            is_featured=True,
            feature_type='bestseller'
        )

        cashew_butter = Product.objects.create(
            category=nut_butters,
            name='Creamy Cashew Butter',
            description='Smooth and creamy cashew butter with a delicate flavor. Made from premium cashews and nothing else.',
            price=35.00,
            size='290g',
            slug='creamy-cashew-butter'
        )

        honey_peanut_butter = Product.objects.create(
            category=nut_butters,
            name='Honey Peanut Butter',
            description='Our classic peanut butter with a touch of natural honey for a sweet twist. Perfect for Mother\'s Day gift baskets!',
            price=25.00,
            size='400g',
            slug='honey-peanut-butter',
            is_featured=True,
            feature_type='seasonal'
        )

        # Create product variants
        ProductVariant.objects.create(
            product=peanut_butter,
            name='Extra Ground',
            additional_price=0.00
        )

        ProductVariant.objects.create(
            product=peanut_butter,
            name='Mega Crunch',
            additional_price=2.00
        )

        # Create product ingredients
        ProductIngredient.objects.create(
            product=peanut_butter,
            ingredient=peanuts,
            percentage=100.00
        )

        ProductIngredient.objects.create(
            product=cashew_butter,
            ingredient=cashews,
            percentage=100.00
        )

        ProductIngredient.objects.create(
            product=honey_peanut_butter,
            ingredient=peanuts,
            percentage=90.00
        )

        ProductIngredient.objects.create(
            product=honey_peanut_butter,
            ingredient=honey,
            percentage=10.00
        )

        self.stdout.write(self.style.SUCCESS('Initial data created successfully!'))
