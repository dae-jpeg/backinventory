from django.db import migrations, models
import django.db.models.deletion
import django.core.validators
import uuid
from django.utils import timezone

def create_default_data(apps, schema_editor):
    Company = apps.get_model('api', 'Company')
    Region = apps.get_model('api', 'Region')
    CustomUser = apps.get_model('api', 'CustomUser')
    Branch = apps.get_model('api', 'Branch')
    Category = apps.get_model('api', 'Category')
    CompanyMembership = apps.get_model('api', 'CompanyMembership')
    
    # Create default admin user
    default_user, user_created = CustomUser.objects.get_or_create(
        username='admin',
        defaults={
            'id': uuid.uuid4(),
            'first_name': 'Admin',
            'last_name': 'User',
            'email': 'admin@example.com',
            'is_staff': True,
            'is_superuser': True,
            'date_joined': timezone.now(),
            'global_user_level': 'BOSS_DEVELOPER',
        }
    )
    
    # Create default company
    default_company, company_created = Company.objects.get_or_create(
        name='Default Company',
        defaults={
            'id': uuid.uuid4(),
            'description': 'Default company for the system',
            'created_at': timezone.now(),
            'updated_at': timezone.now(),
            'owner': default_user,
        }
    )
    
    # Create default branch
    default_branch, branch_created = Branch.objects.get_or_create(
        name='Main Branch',
        company=default_company,
        defaults={
            'id': uuid.uuid4(),
            'description': 'Main branch for the default company',
            'created_at': timezone.now(),
            'updated_at': timezone.now(),
        }
    )
    
    # Create default category
    default_category, category_created = Category.objects.get_or_create(
        name='General',
        company=default_company,
        defaults={
            'id': uuid.uuid4(),
            'created_at': timezone.now(),
            'updated_at': timezone.now(),
        }
    )
    
    # Assign existing regions to default company
    Region.objects.filter(company_id__isnull=True).update(company=default_company)
    
    # Create company membership for admin
    CompanyMembership.objects.get_or_create(
        user=default_user,
        company=default_company,
        defaults={
            'id': uuid.uuid4(),
            'role': 'SUPERVISOR',
        }
    )

def reverse_default_data(apps, schema_editor):
    pass

class Migration(migrations.Migration):

    dependencies = [
        ('api', '0010_update_user_levels'),
    ]

    operations = [
        # Create Company model
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
        
        # Create Branch model
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
        
        # Create Category model
        migrations.CreateModel(
            name='Category',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True)),
                ('name', models.CharField(max_length=50)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('company', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='categories', to='api.company')),
                ('branch', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='categories', to='api.branch')),
            ],
            options={
                'verbose_name': 'Category',
                'verbose_name_plural': 'Categories',
                'ordering': ['name'],
                'unique_together': {('company', 'name', 'branch')},
            },
        ),
        
        # Create CompanyMembership model
        migrations.CreateModel(
            name='CompanyMembership',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True)),
                ('role', models.CharField(choices=[('SUPERVISOR', 'Supervisor'), ('BRANCH_MANAGER', 'Branch Manager'), ('USER', 'User')], max_length=15)),
                ('company', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='members', to='api.company')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='company_memberships', to='api.customuser')),
                ('branch', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='api.branch')),
            ],
            options={
                'verbose_name': 'Company Membership',
                'verbose_name_plural': 'Company Memberships',
                'unique_together': {('user', 'company')},
            },
        ),
        
        # Add company field to regions
        migrations.AddField(
            model_name='region',
            name='company',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='api.company'),
        ),
        
        # Add branch field to customuser
        migrations.AddField(
            model_name='customuser',
            name='branch',
            field=models.ForeignKey(blank=True, help_text='The branch this user belongs to (for Managers and Users).', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='staff', to='api.branch'),
        ),
        
        # Add global_user_level field to customuser
        migrations.AddField(
            model_name='customuser',
            name='global_user_level',
            field=models.CharField(choices=[('BOSS_DEVELOPER', 'Boss/Developer'), ('MEMBER', 'Member')], default='MEMBER', max_length=15),
        ),
        
        # Update customuser model options
        migrations.AlterModelOptions(
            name='customuser',
            options={'verbose_name': 'user', 'verbose_name_plural': 'users'},
        ),
        
        migrations.AlterUniqueTogether(
            name='customuser',
            unique_together=set(),
        ),
        
        # Update id_number field
        migrations.AlterField(
            model_name='customuser',
            name='id_number',
            field=models.CharField(default='00000000', help_text='Required. Enter a unique ID number (digits only).', max_length=20, unique=True, validators=[django.core.validators.RegexValidator(message='ID number must contain only digits', regex='^[0-9]+$')]),
        ),
        
        # Add quantity field to transaction
        migrations.AddField(
            model_name='transaction',
            name='quantity',
            field=models.PositiveIntegerField(default=1),
        ),
        
        # Run data migration
        migrations.RunPython(create_default_data, reverse_default_data),
        
        # Make company field required for regions
        migrations.AlterField(
            model_name='region',
            name='company',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='api.company'),
        ),
    ] 