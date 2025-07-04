from django.core.management.base import BaseCommand
from api.models import Item

class Command(BaseCommand):
    help = 'Fix items that have no original stock quantity set'

    def add_arguments(self, parser):
        parser.add_argument(
            '--item-name',
            type=str,
            help='Specific item name to fix (optional)',
        )
        parser.add_argument(
            '--set-to-current',
            action='store_true',
            help='Set original stock to current stock quantity',
        )
        parser.add_argument(
            '--set-to',
            type=int,
            help='Set original stock to a specific quantity',
        )
        parser.add_argument(
            '--fix-zero-original',
            action='store_true',
            help='Fix items with 0 original stock but current stock > 0',
        )
        parser.add_argument(
            '--fix-with-transactions',
            action='store_true',
            help='Fix items by calculating original stock from transaction history',
        )

    def handle(self, *args, **options):
        items = Item.objects.all()
        
        if options['item_name']:
            items = items.filter(name__icontains=options['item_name'])
        
        if options['fix_zero_original']:
            # Find items with 0 original stock but current stock > 0
            items_to_fix = items.filter(original_stock_quantity=0, stock_quantity__gt=0)
            
            if not items_to_fix.exists():
                self.stdout.write(
                    self.style.WARNING('No items found with 0 original stock but current stock > 0.')
                )
                return
            
            self.stdout.write(f'Found {items_to_fix.count()} items to fix:')
            for item in items_to_fix:
                self.stdout.write(f'  - {item.name}: current={item.stock_quantity}, original=0')
            
            # Update them to set original_stock_quantity = stock_quantity
            for item in items_to_fix:
                item.original_stock_quantity = item.stock_quantity
                item.save()
                self.stdout.write(
                    self.style.SUCCESS(f'Fixed {item.name}: original_stock_quantity set to {item.stock_quantity}')
                )
            return
        
        if options['fix_with_transactions']:
            # Find items with 0 original stock and calculate from transaction history
            items_to_fix = items.filter(original_stock_quantity=0)
            
            if not items_to_fix.exists():
                self.stdout.write(
                    self.style.WARNING('No items found with 0 original stock quantity.')
                )
                return
            
            self.stdout.write(f'Found {items_to_fix.count()} items to fix using transaction history:')
            
            for item in items_to_fix:
                # Calculate original stock from transaction history
                from api.models import Transaction
                
                # Get all transactions for this item
                transactions = Transaction.objects.filter(item=item)
                
                # Calculate original stock: current stock + total withdrawn - total returned
                total_withdrawn = sum(t.quantity for t in transactions if t.transaction_type == 'WITHDRAW')
                total_returned = sum(t.quantity for t in transactions if t.transaction_type == 'RETURN')
                
                calculated_original = item.stock_quantity + total_withdrawn - total_returned
                
                if calculated_original > 0:
                    item.original_stock_quantity = calculated_original
                    item.save()
                    self.stdout.write(
                        self.style.SUCCESS(f'Fixed {item.name}: original_stock_quantity set to {calculated_original} (current: {item.stock_quantity}, withdrawn: {total_withdrawn}, returned: {total_returned})')
                    )
                else:
                    self.stdout.write(
                        self.style.WARNING(f'Could not calculate original stock for {item.name}: calculated value is {calculated_original}')
                    )
            return
        
        # Filter items with no original stock quantity
        items_with_no_original = items.filter(original_stock_quantity=0)
        
        if not items_with_no_original.exists():
            self.stdout.write(
                self.style.SUCCESS('No items found with 0 original stock quantity.')
            )
            return
        
        self.stdout.write(f'Found {items_with_no_original.count()} items with 0 original stock quantity:')
        for item in items_with_no_original:
            self.stdout.write(f'  - {item.name}: current stock={item.stock_quantity}, original=0')
        
        if options['set_to_current']:
            # Set original stock to current stock
            for item in items_with_no_original:
                old_original = item.original_stock_quantity
                item.original_stock_quantity = item.stock_quantity
                item.save()
                self.stdout.write(
                    self.style.SUCCESS(f'Updated {item.name}: original_stock_quantity {old_original} → {item.original_stock_quantity}')
                )
        elif options['set_to'] is not None:
            # Set original stock to specific value
            new_original = options['set_to']
            for item in items_with_no_original:
                old_original = item.original_stock_quantity
                item.original_stock_quantity = new_original
                item.save()
                self.stdout.write(
                    self.style.SUCCESS(f'Updated {item.name}: original_stock_quantity {old_original} → {new_original}')
                )
        else:
            # Just show the items without making changes
            self.stdout.write(
                self.style.WARNING('\nTo fix these items, use one of these options:')
            )
            self.stdout.write('  --set-to-current    # Set original stock to current stock quantity')
            self.stdout.write('  --set-to <number>    # Set original stock to a specific quantity')
            self.stdout.write('  --fix-zero-original  # Fix items with 0 original but current stock > 0')
            self.stdout.write('  --fix-with-transactions  # Calculate original stock from transaction history')
            self.stdout.write('\nExample:')
            self.stdout.write('  python manage.py fix_original_stock --set-to-current')
            self.stdout.write('  python manage.py fix_original_stock --set-to 10')
            self.stdout.write('  python manage.py fix_original_stock --item-name "Cracklings" --set-to 10')
            self.stdout.write('  python manage.py fix_original_stock --fix-with-transactions') 