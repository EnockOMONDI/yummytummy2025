from django.apps import AppConfig


class YummytummyStoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'yummytummy_store'
    verbose_name = 'YummyTummy Store'

    def ready(self):
        """Register signals and keep operational roles in sync after migrations."""
        from django.db.models.signals import post_migrate

        import yummytummy_store.signals
        from yummytummy_store.roles import ensure_operational_groups

        post_migrate.connect(
            ensure_operational_groups,
            dispatch_uid='yummytummy_store.ensure_operational_groups',
        )
