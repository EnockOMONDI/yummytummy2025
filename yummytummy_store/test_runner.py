from django.test.runner import DiscoverRunner


class StoreDiscoverRunner(DiscoverRunner):
    """Keep unlabeled test runs away from legacy root diagnostic scripts."""

    def build_suite(self, test_labels=None, **kwargs):
        labels = test_labels or ('yummytummy_store.tests',)
        return super().build_suite(labels, **kwargs)
