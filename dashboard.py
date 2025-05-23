from django.utils.translation import gettext_lazy as _
from jet.dashboard import modules
from jet.dashboard.dashboard import Dashboard, AppIndexDashboard


class CustomIndexDashboard(Dashboard):
    columns = 3

    def init_with_context(self, context):
        self.available_children.append(modules.LinkList)
        self.available_children.append(modules.Feed)

        # Column 1
        self.children.append(modules.ModelList(
            _('Products'),
            models=('maslove_store.models.Product', 'maslove_store.models.Category', 
                    'maslove_store.models.Ingredient', 'maslove_store.models.ProductVariant',
                    'maslove_store.models.ProductIngredient'),
            column=0,
            order=0
        ))
        
        # Column 2
        self.children.append(modules.ModelList(
            _('Orders'),
            models=('maslove_store.models.Order', 'maslove_store.models.OrderItem'),
            column=1,
            order=0
        ))
        
        self.children.append(modules.ModelList(
            _('Coupons'),
            models=('maslove_store.models.Coupon', 'maslove_store.models.CouponUsage'),
            column=1,
            order=1
        ))
        
        # Column 3
        self.children.append(modules.RecentActions(
            _('Recent Actions'),
            10,
            column=2,
            order=0
        ))
        
        self.children.append(modules.LinkList(
            _('Maslove Resources'),
            children=[
                {
                    'title': _('Maslove Website'),
                    'url': '/',
                    'external': False,
                },
                {
                    'title': _('Django Documentation'),
                    'url': 'https://docs.djangoproject.com/',
                    'external': True,
                },
            ],
            column=2,
            order=1
        ))


class CustomAppIndexDashboard(AppIndexDashboard):
    def init_with_context(self, context):
        self.available_children.append(modules.LinkList)

        self.children.append(modules.ModelList(
            title=_('Application Models'),
            models=self.models(),
            column=0,
            order=0
        ))
        
        self.children.append(modules.RecentActions(
            include_list=self.get_app_content_types(),
            column=1,
            order=0
        ))
