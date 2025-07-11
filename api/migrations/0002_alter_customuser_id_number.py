# Generated by Django 5.2.1 on 2025-06-03 12:22

import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='customuser',
            name='id_number',
            field=models.CharField(blank=True, help_text='Required. Enter a unique ID number (digits only).', max_length=20, null=True, unique=True, validators=[django.core.validators.RegexValidator(message='ID number must contain only digits', regex='^[0-9]+$')]),
        ),
    ]
