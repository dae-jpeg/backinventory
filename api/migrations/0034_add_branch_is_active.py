from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0033_alter_item_unique_together_alter_item_barcode_number_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='branch',
            name='is_active',
            field=models.BooleanField(default=True),
        ),
    ] 