from django.core.management.base import BaseCommand

from yummytummy_store.notifications import NotificationService


class Command(BaseCommand):
    help = 'Retry queued and failed customer notifications.'

    def add_arguments(self, parser):
        parser.add_argument('--limit', type=int, default=50)

    def handle(self, *args, **options):
        processed = NotificationService.process_pending(limit=options['limit'])
        self.stdout.write(self.style.SUCCESS(f'Sent {processed} notification(s).'))
