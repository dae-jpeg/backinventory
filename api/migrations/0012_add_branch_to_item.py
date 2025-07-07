from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0011_complete_setup'),
    ]

    operations = [
        migrations.AddField(
            model_name='item',
            name='branch',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='items',
                to='api.branch',
                null=True,
                blank=True,
                help_text='The branch this item belongs to'
            ),
        ),
    ] 