# Generated manually to add region fields

from django.db import migrations, models
import django.db.models.deletion
import uuid


def create_default_region_and_assign_data(apps, schema_editor):
    """Create a default region and assign existing data to it"""
    Region = apps.get_model('api', 'Region')
    CustomUser = apps.get_model('api', 'CustomUser')
    Item = apps.get_model('api', 'Item')
    Transaction = apps.get_model('api', 'Transaction')
    
    # Create default region
    default_region = Region.objects.create(
        name='Default Region',
        slug='default',
        code='DEFAULT',
        description='Default region for existing data',
        is_active=True
    )
    
    # Assign existing users to default region (except super admin)
    CustomUser.objects.filter(region__isnull=True).update(region=default_region)
    
    # Assign existing items to default region
    Item.objects.filter(region__isnull=True).update(region=default_region)
    
    # Assign existing transactions to default region
    Transaction.objects.filter(region__isnull=True).update(region=default_region)


def reverse_default_region(apps, schema_editor):
    """Reverse the default region assignment"""
    Region = apps.get_model('api', 'Region')
    Region.objects.filter(code='DEFAULT').delete()


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0006_add_region_multi_tenancy'),
    ]

    operations = [
        # Create Region model
        migrations.CreateModel(
            name='Region',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True)),
                ('name', models.CharField(max_length=200, unique=True)),
                ('slug', models.SlugField(help_text='URL-friendly identifier', max_length=100, unique=True)),
                ('code', models.CharField(help_text='Short region code (e.g., R1, R2)', max_length=10, unique=True)),
                ('description', models.TextField(blank=True)),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('max_users', models.PositiveIntegerField(default=100, help_text='Maximum number of users allowed')),
                ('max_items', models.PositiveIntegerField(default=1000, help_text='Maximum number of items allowed')),
                ('logo', models.ImageField(blank=True, null=True, upload_to='region_logos/')),
                ('primary_color', models.CharField(default='#3B82F6', help_text='Primary brand color (hex)', max_length=7)),
                ('secondary_color', models.CharField(default='#1F2937', help_text='Secondary brand color (hex)', max_length=7)),
            ],
            options={
                'ordering': ['name'],
            },
        ),
        
        # Add region field to CustomUser (nullable)
        migrations.AddField(
            model_name='customuser',
            name='region',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='users', to='api.region'),
        ),
        
        # Add region field to Item (nullable initially)
        migrations.AddField(
            model_name='item',
            name='region',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='items', to='api.region'),
        ),
        
        # Add region field to Transaction (nullable initially)
        migrations.AddField(
            model_name='transaction',
            name='region',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='transactions', to='api.region'),
        ),
        
        # Run data migration to create default region and assign existing data
        migrations.RunPython(create_default_region_and_assign_data, reverse_default_region),
        
        # Make region fields required after data migration
        migrations.AlterField(
            model_name='item',
            name='region',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='items', to='api.region'),
        ),
        
        migrations.AlterField(
            model_name='transaction',
            name='region',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='transactions', to='api.region'),
        ),
        
        # Update unique constraints
        migrations.AlterUniqueTogether(
            name='customuser',
            unique_together={('region', 'id_number')},
        ),
        migrations.AlterUniqueTogether(
            name='item',
            unique_together={('region', 'item_id'), ('region', 'barcode_number')},
        ),
    ] 