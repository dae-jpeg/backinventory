# Generated by Django 5.0.4 on 2025-06-23 11:53

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0011_complete_setup'),
    ]

    operations = [
        migrations.AddField(
            model_name='item',
            name='category_fk',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='items_fk', to='api.category'),
        ),
    ]
