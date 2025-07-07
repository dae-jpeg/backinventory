from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0012_add_branch_to_item'),
    ]

    operations = [
        migrations.AddField(
            model_name='transaction',
            name='branch',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='transactions',
                to='api.branch',
                null=True,
                blank=True,
                help_text='The branch where this transaction occurred'
            ),
        ),
    ] 