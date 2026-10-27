from datetime import timedelta
from django.utils import timezone
from django.core.management.base import BaseCommand
from chat.models import Room

class Command(BaseCommand):
    help = 'يقفل الغرف اللي فضلت waiting لأكتر من 24 ساعة'

    def handle(self, *args, **options):
        cutoff = timezone.now() - timedelta(hours=24)
        stale_rooms = Room.objects.filter(status=Room.WAITING, created_at__lt=cutoff)
        count = stale_rooms.update(status=Room.CLOSED)

        self.stdout.write(self.style.SUCCESS(f'اتقفل {count} روم مهجورة'))