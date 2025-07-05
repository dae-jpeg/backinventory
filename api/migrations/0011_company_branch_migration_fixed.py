from django.db import migrations, models
import django.db.models.deletion
import uuid
from django.utils import timezone

def create_default_company_and_assign_regions(apps, schema_editor):
    Company = apps.get_model('api', 'Company')
    Region = apps.get_model('api', 'Region')
    CustomUser = apps.get_model('api', 'CustomUser')
    
    # Get or create a default user for the company owner FIRST
    default_user, user_created = CustomUser.objects.get_or_create(
        username='default_admin',
        defaults={
            'id': uuid.uuid4(),
            'first_name': 'Default',
            'last_name': 'Admin',
            'email': 'admin@default.com',
            'is_staff': True,
            'is_superuser': True,
            'date_joined': timezone.now(),
        }
    )
    
    # Create a default company with the owner already set
    default_company, created = Company.objects.get_or_create(
        name='Default Company',
        defaults={
            'id': uuid.uuid4(),
            'description': 'Default company for existing data',
            'created_at': timezone.now(),
            'updated_at': timezone.now(),
            'owner': default_user,  # Set the owner during creation
        }
    )
    
    # If company already existed, set the owner
    if not created and not default_company.owner_id:
        default_company.owner = default_user
        default_company.save()
    
    # Assign all existing regions to the default company
    Region.objects.filter(company_id__isnull=True).update(company=default_company)

def reverse_default_company(apps, schema_editor):
    # This is optional - you can leave it empty if you don't need to reverse
    pass

class Migration(migrations.Migration):

    dependencies = [
        ('api', '0010_update_user_levels'),
    ]

    operations = [
        # First, create the company model
        migrations.CreateModel(
            name='Company',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True)),
                ('name', models.CharField(max_length=150, unique=True)),
                ('description', models.TextField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('owner', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='owned_companies', to='api.customuser')),
                ('supervisor', models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='supervised_company', to='api.customuser')),
            ],
        ),
        
        # Create the Branch model
        migrations.CreateModel(
            name='Branch',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True)),
                ('name', models.CharField(max_length=100)),
                ('description', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('company', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='branches', to='api.company')),
            ],
            options={
                'verbose_name': 'Branch',
                'verbose_name_plural': 'Branches',
                'ordering': ['company', 'name'],
            },
        ),
        
        # Add company_id to regions (nullable first)
        migrations.AddField(
            model_name='region',
            name='company',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='api.company'),
        ),
        
        # Run the data migration to populate company_id
        migrations.RunPython(create_default_company_and_assign_regions, reverse_default_company),
        
        # Now make company_id required
        migrations.AlterField(
            model_name='region',
            name='company',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='api.company'),
        ),
        
        # Add branch field to CustomUser
        migrations.AddField(
            model_name='customuser',
            name='branch',
            field=models.ForeignKey(blank=True, help_text='The branch this user belongs to (for Managers and Users).', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='staff', to='api.branch'),
        ),
    ] 