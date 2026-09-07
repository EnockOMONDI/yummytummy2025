from django.conf import settings


def owner_dashboard_permission(request):
    return request.user.has_perm('yummytummy_store.view_owner_dashboard')


def environment_callback(request):
    if settings.DEBUG:
        return ['Development', 'warning']
    return ['Production', 'danger']
