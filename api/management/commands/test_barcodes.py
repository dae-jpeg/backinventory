from django.core.management.base import BaseCommand
from api.models import Item

class Command(BaseCommand):
    help = 'Test barcode generation and display barcode information'

    def add_arguments(self, parser):
        parser.add_argument(
            '--generate',
            action='store_true',
            help='Generate barcodes for items that don\'t have them',
        )
        parser.add_argument(
            '--regenerate',
            action='store_true',
            help='Regenerate all barcodes',
        )

    def handle(self, *args, **options):
        items = Item.objects.all()
        
        if not items.exists():
            self.stdout.write(self.style.WARNING('No items found in the database.'))
            return

        self.stdout.write(f'Found {items.count()} items in the database.')
        
        if options['generate']:
            self.stdout.write('Generating barcodes for items without barcodes...')
            for item in items:
                if not item.barcode:
                    item.generate_barcode()
                    item.save()
                    self.stdout.write(f'Generated barcode for {item.name} ({item.item_id})')
        
        if options['regenerate']:
            self.stdout.write('Regenerating all barcodes...')
            for item in items:
                if item.barcode:
                    item.barcode.delete(save=False)
                item.generate_barcode()
                item.save()
                self.stdout.write(f'Regenerated barcode for {item.name} ({item.item_id})')

        # Display barcode information
        self.stdout.write('\n' + '='*80)
        self.stdout.write('BARCODE INFORMATION')
        self.stdout.write('='*80)
        
        for item in items:
            self.stdout.write(f'\nItem: {item.name}')
            self.stdout.write(f'  Item ID: {item.item_id}')
            self.stdout.write(f'  UUID: {item.id}')
            self.stdout.write(f'  Barcode Number: {item.barcode_number}')
            self.stdout.write(f'  Has Barcode Image: {"Yes" if item.barcode else "No"}')
            if item.barcode:
                self.stdout.write(f'  Barcode URL: {item.barcode.url}')
            
            # Show what the scanner should read
            if item.barcode_number:
                self.stdout.write(f'  Scanner should read: {item.barcode_number}')
            else:
                self.stdout.write(f'  Scanner should read: BAR{item.item_id}')
            
            # Show QR code format
            self.stdout.write(f'  QR code format: item:{item.id}')
        
        self.stdout.write('\n' + '='*80)
        self.stdout.write('TESTING SCAN FORMATS')
        self.stdout.write('='*80)
        
        for item in items:
            self.stdout.write(f'\n{item.name}:')
            self.stdout.write(f'  QR Code: item:{item.id}')
            if item.barcode_number:
                self.stdout.write(f'  Barcode: {item.barcode_number}')
            else:
                self.stdout.write(f'  Barcode: BAR{item.item_id}')
        
        self.stdout.write(self.style.SUCCESS('\nBarcode test completed!')) 