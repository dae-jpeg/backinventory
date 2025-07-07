from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0036_fix_user_level_field'),
    ]

    operations = [
        # Recreate the Item table without the region_id NOT NULL constraint
        migrations.RunSQL(
            """
            CREATE TABLE api_item_new (
                id char(32) NOT NULL PRIMARY KEY,
                name varchar(200) NOT NULL,
                description TEXT NOT NULL,
                category_id char(32) NULL,
                status varchar(20) NOT NULL,
                qr_code varchar(100) NULL,
                created_at datetime NOT NULL,
                updated_at datetime NOT NULL,
                barcode varchar(100) NULL,
                barcode_number varchar(50) NULL,
                minimum_stock integer unsigned NOT NULL,
                stock_quantity integer unsigned NOT NULL,
                region_id char(32) NULL,
                created_by_id char(32) NULL,
                original_stock_quantity integer unsigned NOT NULL,
                item_id varchar(50) NULL,
                branch_id char(32) NULL
            );
            INSERT INTO api_item_new SELECT * FROM api_item;
            DROP TABLE api_item;
            ALTER TABLE api_item_new RENAME TO api_item;
            """,
            reverse_sql="""
            CREATE TABLE api_item_old (
                id char(32) NOT NULL PRIMARY KEY,
                name varchar(200) NOT NULL,
                description TEXT NOT NULL,
                category_id char(32) NULL,
                status varchar(20) NOT NULL,
                qr_code varchar(100) NULL,
                created_at datetime NOT NULL,
                updated_at datetime NOT NULL,
                barcode varchar(100) NULL,
                barcode_number varchar(50) NULL,
                minimum_stock integer unsigned NOT NULL,
                stock_quantity integer unsigned NOT NULL,
                region_id char(32) NOT NULL,
                created_by_id char(32) NULL,
                original_stock_quantity integer unsigned NOT NULL,
                item_id varchar(50) NULL,
                branch_id char(32) NULL
            );
            INSERT INTO api_item_old SELECT * FROM api_item;
            DROP TABLE api_item;
            ALTER TABLE api_item_old RENAME TO api_item;
            """
        ),
    ] 