from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from api.models import Region, CustomUser, Item, Transaction
from django.db import transaction
import uuid

User = get_user_model()

class Command(BaseCommand):
    help = 'Setup multi-tenancy with regions and sample data'

    def add_arguments(self, parser):
        parser.add_argument(
            '--create-super-admin',
            action='store_true',
            help='Create a super admin user',
        )
        parser.add_argument(
            '--create-sample-regions',
            action='store_true',
            help='Create sample regions',
        )
        parser.add_argument(
            '--create-sample-data',
            action='store_true',
            help='Create sample users and items',
        )

    def handle(self, *args, **options):
        if options['create_super_admin']:
            self.create_super_admin()
        
        if options['create_sample_regions']:
            self.create_sample_regions()
        
        if options['create_sample_data']:
            self.create_sample_data()

    def create_super_admin(self):
        """Create a developer user"""
        try:
            # Create developer without region (can access all regions)
            super_admin, created = CustomUser.objects.get_or_create(
                id_number='99999999',
                defaults={
                    'username': 'developer',
                    'email': 'boss@example.com',
                    'first_name': 'Boss',
                    'last_name': 'Developer',
                    'user_level': 'DEVELOPER',
                    'is_staff': True,
                    'is_superuser': True,
                    'region': None,  # Developer has no region restriction
                }
            )
            
            if created:
                super_admin.set_password('admin123')
                super_admin.save()
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Developer created successfully: {super_admin.username} (ID: {super_admin.id_number})'
                    )
                )
            else:
                self.stdout.write(
                    self.style.WARNING('Developer already exists')
                )
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error creating developer: {e}')
            )

    def create_sample_regions(self):
        """Create sample regions"""
        regions_data = [
            {
                'name': 'Region 1 - North Campus',
                'slug': 'region1',
                'code': 'R1',
                'description': 'North Campus region for academic and administrative activities',
                'primary_color': '#3B82F6',
                'secondary_color': '#1F2937',
            },
            {
                'name': 'Region 2 - South Campus',
                'slug': 'region2',
                'code': 'R2',
                'description': 'South Campus region for research and development',
                'primary_color': '#10B981',
                'secondary_color': '#064E3B',
            },
            {
                'name': 'Region 3 - East Campus',
                'slug': 'region3',
                'code': 'R3',
                'description': 'East Campus region for student services and facilities',
                'primary_color': '#F59E0B',
                'secondary_color': '#92400E',
            },
        ]

        for region_data in regions_data:
            region, created = Region.objects.get_or_create(
                code=region_data['code'],
                defaults=region_data
            )
            
            if created:
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Region created: {region.name} ({region.code})'
                    )
                )
            else:
                self.stdout.write(
                    self.style.WARNING(
                        f'Region already exists: {region.name} ({region.code})'
                    )
                )

    def create_sample_data(self):
        """Create sample users and items for each region"""
        regions = Region.objects.filter(is_active=True)
        
        if not regions.exists():
            self.stdout.write(
                self.style.ERROR('No active regions found. Please create regions first.')
            )
            return

        for region in regions:
            self.create_region_data(region)

    def create_region_data(self, region):
        """Create sample data for a specific region"""
        self.stdout.write(f'Creating sample data for {region.name}...')
        
        # Create region admin
        admin_user, admin_created = CustomUser.objects.get_or_create(
            id_number=f'1000{region.code[-1]}',  # 10001, 10002, etc.
            region=region,
            defaults={
                'username': f'admin_{region.slug}',
                'email': f'admin@{region.slug}.example.com',
                'first_name': f'Admin',
                'last_name': region.name.split()[1],  # "North", "South", etc.
                'user_level': 'ADMIN',
                'department': 'Administration',
                'contact_number': f'555-{region.code[-1]}000',
            }
        )
        
        if admin_created:
            admin_user.set_password('admin123')
            admin_user.save()
            self.stdout.write(f'  - Admin user created: {admin_user.username}')

        # Create region supervisor
        admin_user, admin_created = CustomUser.objects.get_or_create(
            id_number=f'1000{region.code[-1]}',  # 10001, 10002, etc.
            region=region,
            defaults={
                'username': f'supervisor_{region.slug}',
                'email': f'supervisor@{region.slug}.example.com',
                'first_name': f'Supervisor',
                'last_name': region.name.split()[1],  # "North", "South", etc.
                'user_level': 'SUPERVISOR',
                'department': 'Administration',
                'contact_number': f'555-{region.code[-1]}000',
            }
        )
        
        if admin_created:
            admin_user.set_password('admin123')
            admin_user.save()
            self.stdout.write(f'  - Supervisor created: {admin_user.username}')

        # Create branch manager
        staff_user, staff_created = CustomUser.objects.get_or_create(
            id_number=f'2000{region.code[-1]}',  # 20001, 20002, etc.
            region=region,
            defaults={
                'username': f'branch_manager_{region.slug}',
                'email': f'manager@{region.slug}.example.com',
                'first_name': f'Branch',
                'last_name': 'Manager',
                'user_level': 'BRANCH_MANAGER',
                'department': 'Operations',
                'contact_number': f'555-{region.code[-1]}001',
            }
        )
        
        if staff_created:
            staff_user.set_password('staff123')
            staff_user.save()
            self.stdout.write(f'  - Branch Manager created: {staff_user.username}')

        # Create regular users
        for i in range(1, 4):  # Create 3 regular users per region
            user_number = f'{3000 + i}{region.code[-1]}'  # 30011, 30021, etc.
            user, user_created = CustomUser.objects.get_or_create(
                id_number=user_number,
                region=region,
                defaults={
                    'username': f'user{i}_{region.slug}',
                    'email': f'user{i}@{region.slug}.example.com',
                    'first_name': f'User{i}',
                    'last_name': region.name.split()[1],
                    'user_level': 'USER',
                    'department': 'General',
                    'contact_number': f'555-{region.code[-1]}{i:02d}',
                }
            )
            
            if user_created:
                user.set_password('user123')
                user.save()
                self.stdout.write(f'  - User created: {user.username}')

        # Create sample items
        items_data = [
            {
                'item_id': f'LAPTOP-{region.code}-001',
                'name': f'Laptop {region.name}',
                'description': f'High-performance laptop for {region.name}',
                'category': 'ELECTRONICS',
                'status': 'AVAILABLE',
                'stock_quantity': 5,
                'minimum_stock': 2,
            },
            {
                'item_id': f'PROJECTOR-{region.code}-001',
                'name': f'Projector {region.name}',
                'description': f'HD projector for {region.name}',
                'category': 'ELECTRONICS',
                'status': 'AVAILABLE',
                'stock_quantity': 3,
                'minimum_stock': 1,
            },
            {
                'item_id': f'HEADPHONES-{region.code}-001',
                'name': f'Headphones {region.name}',
                'description': f'Noise-cancelling headphones for {region.name}',
                'category': 'AUDIO',
                'status': 'AVAILABLE',
                'stock_quantity': 10,
                'minimum_stock': 3,
            },
        ]

        for item_data in items_data:
            item, item_created = Item.objects.get_or_create(
                item_id=item_data['item_id'],
                region=region,
                defaults=item_data
            )
            
            if item_created:
                self.stdout.write(f'  - Item created: {item.name}')

        # Create sample transactions
        users = CustomUser.objects.filter(region=region, user_level='USER')[:2]
        items = Item.objects.filter(region=region, status='AVAILABLE')[:2]
        
        for i, (user, item) in enumerate(zip(users, items)):
            if i == 0:  # First user withdraws item
                transaction, trans_created = Transaction.objects.get_or_create(
                    item=item,
                    user=user,
                    transaction_type='WITHDRAW',
                    region=region,
                    defaults={
                        'notes': f'Sample withdrawal for {region.name}',
                    }
                )
                
                if trans_created:
                    self.stdout.write(f'  - Transaction created: {user.first_name} withdrew {item.name}')
            else:  # Second user returns item
                transaction, trans_created = Transaction.objects.get_or_create(
                    item=item,
                    user=user,
                    transaction_type='RETURN',
                    region=region,
                    defaults={
                        'notes': f'Sample return for {region.name}',
                    }
                )
                
                if trans_created:
                    self.stdout.write(f'  - Transaction created: {user.first_name} returned {item.name}')

        self.stdout.write(
            self.style.SUCCESS(f'Sample data created successfully for {region.name}')
        ) 