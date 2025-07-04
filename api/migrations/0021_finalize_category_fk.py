from django.db import migrations

def forwards_func(apps, schema_editor):
    # Drop the old string category column
    schema_editor.execute('ALTER TABLE api_item DROP COLUMN category;')
    # Rename category_fk_id to category_id
    schema_editor.execute('ALTER TABLE api_item RENAME COLUMN category_fk_id TO category_id;')

def backwards_func(apps, schema_editor):
    # Add back the string category column (empty)
    schema_editor.execute("ALTER TABLE api_item ADD COLUMN category varchar(50);")
    # Rename category_id back to category_fk_id
    schema_editor.execute('ALTER TABLE api_item RENAME COLUMN category_id TO category_fk_id;')

class Migration(migrations.Migration):
    dependencies = [
        ('api', '0019_migrate_item_category_to_fk'),
    ]
    operations = [
        migrations.RunPython(forwards_func, backwards_func),
    ] 