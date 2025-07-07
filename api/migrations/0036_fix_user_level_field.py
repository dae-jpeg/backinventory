from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0035_merge_20250707_1015'),
    ]

    operations = [
        # Remove the old user_level field since we're using global_user_level
        migrations.RemoveField(
            model_name='customuser',
            name='user_level',
        ),
    ] 