from django.contrib.auth.models import Group, Permission


ROLE_PERMISSIONS = {
    'Sales Team': {
        'product': {'view'},
        'productvariant': {'view'},
        'coupon': {'view'},
        'order': {'add', 'change', 'view'},
        'orderitem': {'view'},
        'recipeorderitem': {'view'},
        'ordertrackingstatus': {'add', 'view'},
        'payment': {'view'},
        'paymentattempt': {'view'},
    },
    'Catalog Managers': {
        'category': {'add', 'change', 'delete', 'view'},
        'ingredient': {'add', 'change', 'delete', 'view'},
        'product': {'add', 'change', 'delete', 'view'},
        'productvariant': {'add', 'change', 'delete', 'view'},
        'productingredient': {'add', 'change', 'delete', 'view'},
    },
    'Fulfillment Team': {
        'order': {'change', 'view'},
        'orderitem': {'view'},
        'recipeorderitem': {'view'},
        'ordertrackingstatus': {'add', 'view'},
        'product': {'view'},
        'productvariant': {'view'},
        'notificationoutbox': {'view'},
    },
    'Finance Team': {
        'order': {'view'},
        'orderitem': {'view'},
        'recipeorderitem': {'view'},
        'payment': {'change', 'view'},
        'paymentattempt': {'view'},
        'paymentproviderevent': {'view'},
        'refund': {'add', 'change', 'view'},
        'coupon': {'view'},
        'couponusage': {'view'},
    },
    'Content Editors': {
        'recipecategory': {'add', 'change', 'delete', 'view'},
        'recipe': {'add', 'change', 'delete', 'view'},
        'recipepurchase': {'view'},
        'recipeorderitem': {'view'},
        'product': {'view'},
    },
    'Marketing Managers': {
        'coupon': {'add', 'change', 'delete', 'view'},
        'couponusage': {'view'},
        'order': {'view'},
        'product': {'view'},
    },
    'Support Team': {
        'order': {'view'},
        'orderitem': {'view'},
        'recipeorderitem': {'view'},
        'ordertrackingstatus': {'add', 'view'},
        'payment': {'view'},
        'paymentattempt': {'view'},
        'notificationoutbox': {'view'},
        'autocreatedaccount': {'view'},
    },
}


def ensure_operational_groups(sender, **kwargs):
    """Create stable least-privilege groups without assigning any users."""
    app_label = 'yummytummy_store'
    for group_name, model_permissions in ROLE_PERMISSIONS.items():
        group, _ = Group.objects.get_or_create(name=group_name)
        codenames = {
            f'{action}_{model_name}'
            for model_name, actions in model_permissions.items()
            for action in actions
        }
        permissions = Permission.objects.filter(
            content_type__app_label=app_label,
            codename__in=codenames,
        )
        group.permissions.set(permissions)
