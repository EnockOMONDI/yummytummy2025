from django.core.management.base import BaseCommand
from yummytummy_store.models import RecipeCategory, Recipe, Product
import json


class Command(BaseCommand):
    help = 'Create sample recipe data for YummyTummy'

    def handle(self, *args, **options):
        self.stdout.write('Creating sample recipe categories...')
        
        # Create Recipe Categories
        categories_data = [
            {
                'name': 'Breakfast',
                'description': 'Start your day with nutritious peanut-based breakfast recipes'
            },
            {
                'name': 'Snacks',
                'description': 'Healthy and delicious peanut snacks for any time of day'
            },
            {
                'name': 'Desserts',
                'description': 'Sweet treats featuring our premium peanut products'
            },
            {
                'name': 'Main Course',
                'description': 'Hearty meals with peanuts as the star ingredient'
            },
            {
                'name': 'Protein Shakes',
                'description': 'Nutritious protein-packed smoothies and shakes'
            }
        ]
        
        categories = {}
        for cat_data in categories_data:
            category, created = RecipeCategory.objects.get_or_create(
                name=cat_data['name'],
                defaults={'description': cat_data['description']}
            )
            categories[cat_data['name']] = category
            if created:
                self.stdout.write(f'Created category: {category.name}')
            else:
                self.stdout.write(f'Category already exists: {category.name}')

        self.stdout.write('Creating sample recipes...')
        
        # Sample Recipes Data
        recipes_data = [
            {
                'title': 'Quick Peanut Butter Protein Smoothie',
                'category': 'Protein Shakes',
                'description': 'A delicious and nutritious protein smoothie perfect for post-workout recovery or a quick breakfast on the go.',
                'ingredients': [
                    '2 tablespoons YummyTummy Peanut Butter',
                    '1 banana, frozen',
                    '1 cup almond milk',
                    '1 scoop vanilla protein powder',
                    '1 tablespoon honey',
                    '1/2 cup ice cubes',
                    '1 teaspoon vanilla extract'
                ],
                'instructions': [
                    'Add all ingredients to a high-speed blender',
                    'Blend on high for 60-90 seconds until smooth and creamy',
                    'Check consistency and add more almond milk if needed',
                    'Pour into a tall glass and serve immediately',
                    'Garnish with a sprinkle of crushed peanuts if desired'
                ],
                'prep_time_minutes': 5,
                'cook_time_minutes': 0,
                'servings': 1,
                'difficulty': 'easy',
                'tags': 'protein, smoothie, quick, healthy, post-workout',
                'preview_content': 'This protein-packed smoothie combines the rich taste of YummyTummy peanut butter with banana and protein powder for the perfect post-workout drink. Ready in just 5 minutes!',
                'is_featured': True
            },
            {
                'title': 'Crunchy Peanut Energy Balls',
                'category': 'Snacks',
                'description': 'No-bake energy balls packed with peanuts, dates, and natural sweetness. Perfect for a quick energy boost.',
                'ingredients': [
                    '1 cup YummyTummy Roasted Peanuts',
                    '1 cup pitted dates, soaked',
                    '2 tablespoons YummyTummy Peanut Butter',
                    '1 tablespoon chia seeds',
                    '1 tablespoon coconut oil',
                    '1 teaspoon vanilla extract',
                    '1/4 cup rolled oats',
                    'Pinch of sea salt'
                ],
                'instructions': [
                    'Soak dates in warm water for 10 minutes to soften',
                    'In a food processor, pulse peanuts until roughly chopped',
                    'Add drained dates and process until a paste forms',
                    'Add peanut butter, chia seeds, coconut oil, and vanilla',
                    'Process until mixture holds together when pressed',
                    'Roll mixture into 12-15 small balls',
                    'Refrigerate for 30 minutes before serving',
                    'Store in refrigerator for up to 1 week'
                ],
                'prep_time_minutes': 20,
                'cook_time_minutes': 0,
                'servings': 12,
                'difficulty': 'easy',
                'tags': 'no-bake, energy, healthy, snack, dates',
                'preview_content': 'These no-bake energy balls are the perfect healthy snack! Made with our premium roasted peanuts and natural dates, they provide sustained energy without any artificial ingredients.',
                'is_featured': False
            },
            {
                'title': 'African Peanut Stew',
                'category': 'Main Course',
                'description': 'A hearty and flavorful African-inspired stew featuring YummyTummy peanuts as the star ingredient.',
                'ingredients': [
                    '1 cup YummyTummy Roasted Peanuts, ground',
                    '2 lbs chicken, cut into pieces',
                    '2 onions, diced',
                    '3 tomatoes, chopped',
                    '3 cloves garlic, minced',
                    '2 tablespoons YummyTummy Peanut Butter',
                    '4 cups chicken broth',
                    '2 sweet potatoes, cubed',
                    '1 bunch spinach, chopped',
                    '2 teaspoons ginger, grated',
                    'Salt and pepper to taste',
                    '2 tablespoons vegetable oil'
                ],
                'instructions': [
                    'Heat oil in a large pot over medium-high heat',
                    'Brown chicken pieces on all sides, then remove and set aside',
                    'Sauté onions until translucent, about 5 minutes',
                    'Add garlic and ginger, cook for 1 minute',
                    'Add tomatoes and cook until softened',
                    'Stir in ground peanuts and peanut butter',
                    'Gradually add chicken broth, stirring constantly',
                    'Return chicken to pot, add sweet potatoes',
                    'Simmer for 30-40 minutes until chicken is tender',
                    'Add spinach in the last 5 minutes of cooking',
                    'Season with salt and pepper to taste',
                    'Serve hot with rice or bread'
                ],
                'prep_time_minutes': 25,
                'cook_time_minutes': 45,
                'servings': 6,
                'difficulty': 'medium',
                'tags': 'african, stew, hearty, traditional, dinner',
                'preview_content': 'Experience the rich flavors of Africa with this traditional peanut stew. Our premium ground peanuts create a creamy, protein-rich base that pairs perfectly with tender chicken and vegetables.',
                'is_featured': True
            },
            {
                'title': 'Peanut Butter Banana Pancakes',
                'category': 'Breakfast',
                'description': 'Fluffy pancakes with a delicious peanut butter twist, perfect for weekend breakfast.',
                'ingredients': [
                    '1 1/2 cups all-purpose flour',
                    '3 tablespoons YummyTummy Peanut Butter',
                    '2 tablespoons sugar',
                    '2 teaspoons baking powder',
                    '1/2 teaspoon salt',
                    '1 1/4 cups milk',
                    '1 egg',
                    '2 tablespoons melted butter',
                    '1 banana, sliced',
                    'Chopped YummyTummy Peanuts for garnish'
                ],
                'instructions': [
                    'In a large bowl, whisk together flour, sugar, baking powder, and salt',
                    'In another bowl, mix milk, egg, melted butter, and peanut butter',
                    'Pour wet ingredients into dry ingredients and stir until just combined',
                    'Heat a griddle or large skillet over medium heat',
                    'Pour 1/4 cup batter for each pancake',
                    'Cook until bubbles form on surface, then flip',
                    'Cook until golden brown on both sides',
                    'Serve hot with banana slices and chopped peanuts',
                    'Drizzle with honey or maple syrup if desired'
                ],
                'prep_time_minutes': 15,
                'cook_time_minutes': 20,
                'servings': 4,
                'difficulty': 'easy',
                'tags': 'pancakes, breakfast, banana, weekend, family',
                'preview_content': 'Start your morning right with these fluffy peanut butter pancakes! Made with our creamy peanut butter and topped with fresh bananas and crunchy peanuts.',
                'is_featured': False
            },
            {
                'title': 'Chocolate Peanut Butter Brownies',
                'category': 'Desserts',
                'description': 'Rich, fudgy brownies with swirls of creamy peanut butter - the perfect indulgent treat.',
                'ingredients': [
                    '1/2 cup YummyTummy Peanut Butter',
                    '1/2 cup butter',
                    '1 cup dark chocolate chips',
                    '3/4 cup brown sugar',
                    '2 large eggs',
                    '1 teaspoon vanilla extract',
                    '1/2 cup all-purpose flour',
                    '1/4 cup cocoa powder',
                    '1/4 teaspoon salt',
                    '1/2 cup chopped YummyTummy Peanuts'
                ],
                'instructions': [
                    'Preheat oven to 350°F (175°C) and line an 8x8 pan with parchment',
                    'Melt butter and chocolate chips in a double boiler',
                    'Stir in brown sugar until combined, then cool slightly',
                    'Beat in eggs one at a time, then vanilla',
                    'Fold in flour, cocoa powder, and salt until just combined',
                    'Pour batter into prepared pan',
                    'Drop spoonfuls of peanut butter over batter',
                    'Use a knife to create swirl patterns',
                    'Sprinkle with chopped peanuts',
                    'Bake for 25-30 minutes until set',
                    'Cool completely before cutting into squares'
                ],
                'prep_time_minutes': 20,
                'cook_time_minutes': 30,
                'servings': 16,
                'difficulty': 'medium',
                'tags': 'brownies, chocolate, dessert, indulgent, baking',
                'preview_content': 'Indulge in these decadent chocolate brownies swirled with our creamy peanut butter. Each bite combines rich chocolate with the perfect amount of peanut flavor.',
                'is_featured': True
            }
        ]

        # Get some products for related products
        products = list(Product.objects.all()[:3])
        
        for recipe_data in recipes_data:
            category = categories[recipe_data['category']]
            
            recipe, created = Recipe.objects.get_or_create(
                title=recipe_data['title'],
                defaults={
                    'category': category,
                    'description': recipe_data['description'],
                    'ingredients': recipe_data['ingredients'],
                    'instructions': recipe_data['instructions'],
                    'prep_time_minutes': recipe_data['prep_time_minutes'],
                    'cook_time_minutes': recipe_data['cook_time_minutes'],
                    'servings': recipe_data['servings'],
                    'difficulty': recipe_data['difficulty'],
                    'price': 100.00,  # KES 100 as specified
                    'tags': recipe_data['tags'],
                    'preview_content': recipe_data['preview_content'],
                    'is_published': True,
                    'is_featured': recipe_data['is_featured']
                }
            )
            
            if created:
                # Add some related products
                if products:
                    recipe.related_products.set(products[:2])
                self.stdout.write(f'Created recipe: {recipe.title}')
            else:
                self.stdout.write(f'Recipe already exists: {recipe.title}')

        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully created sample recipe data!\n'
                f'Categories: {RecipeCategory.objects.count()}\n'
                f'Recipes: {Recipe.objects.count()}'
            )
        )
