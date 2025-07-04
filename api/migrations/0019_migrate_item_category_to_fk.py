from django.db import migrations
import uuid

def forwards_func(apps, schema_editor):
    Item = apps.get_model('api', 'Item')
    Category = apps.get_model('api', 'Category')
    Branch = apps.get_model('api', 'Branch')
    Company = apps.get_model('api', 'Company')
    db_alias = schema_editor.connection.alias

    # For each unique category string, create a Category if needed
    unique_categories = set(Item.objects.using(db_alias).values_list('category', flat=True))
    cat_map = {}
    for cat_name in unique_categories:
        if not cat_name or cat_name == '':
            continue
        # Use the first item's branch and company for this category
        first_item = Item.objects.using(db_alias).filter(category=cat_name).first()
        branch = first_item.branch if first_item else None
        company = branch.company if branch else None
        if not company:
            continue  # skip if no company can be determined
        cat_obj, _ = Category.objects.using(db_alias).get_or_create(
            name=cat_name,
            company=company,
            branch=branch
        )
        cat_map[(cat_name, company.id, branch.id if branch else None)] = cat_obj
    # Set category_fk for each item
    for item in Item.objects.using(db_alias).all():
        branch = item.branch
        company = branch.company if branch else None
        key = (item.category, company.id if company else None, branch.id if branch else None)
        cat_obj = cat_map.get(key)
        if cat_obj:
            item.category_fk = cat_obj
            item.save()

def backwards_func(apps, schema_editor):
    # Not strictly needed, but could set category string from category_fk
    Item = apps.get_model('api', 'Item')
    db_alias = schema_editor.connection.alias
    for item in Item.objects.using(db_alias).all():
        if item.category_fk:
            item.category = item.category_fk.name
            item.save()

class Migration(migrations.Migration):
    dependencies = [
        ('api', '0018_item_category_fk_alter_item_category'),
    ]
    operations = [
        migrations.RunPython(forwards_func, backwards_func),
    ] 