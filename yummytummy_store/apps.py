from django.apps import AppConfig


class YummytummyStoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'yummytummy_store'

    def ready(self):
        """Import signals when the app is ready"""
        import yummytummy_store.signals
