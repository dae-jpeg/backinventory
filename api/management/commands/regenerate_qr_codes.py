from django.core.management.base import BaseCommand
from api.models import Item

class Command(BaseCommand):
    help = 'Regenerates QR codes for all items'

    def handle(self, *args, **options):
        items = Item.objects.all()
        total = items.count()
        
        self.stdout.write(f'Found {total} items. Starting QR code regeneration...')
        
        for i, item in enumerate(items, 1):
            old_qr = item.qr_code
            if old_qr:
                old_qr.delete(save=False)
            item.generate_qr()
            item.save()
            self.stdout.write(f'Regenerated QR code for item {i}/{total}: {item.name} ({item.item_id})')
        
        self.stdout.write(self.style.SUCCESS('Successfully regenerated all QR codes!')) 