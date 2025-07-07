from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0037_fix_region_id_constraint'),
    ]

    operations = [
        # Remove region_id column from api_transaction table
        migrations.RunSQL(
            """
            CREATE TABLE api_transaction_new (
                id char(32) NOT NULL PRIMARY KEY,
                branch_id char(32) NOT NULL,
                item_id char(32) NOT NULL,
                user_id char(32) NOT NULL,
                transaction_type varchar(10) NOT NULL,
                quantity integer unsigned NOT NULL,
                timestamp datetime NOT NULL,
                notes TEXT NOT NULL,
                reference_number varchar(20) NULL
            );
            INSERT INTO api_transaction_new SELECT 
                id, branch_id, item_id, user_id, transaction_type, 
                quantity, timestamp, notes, reference_number 
            FROM api_transaction;
            DROP TABLE api_transaction;
            ALTER TABLE api_transaction_new RENAME TO api_transaction;
            """,
            reverse_sql="""
            CREATE TABLE api_transaction_old (
                id char(32) NOT NULL PRIMARY KEY,
                branch_id char(32) NOT NULL,
                item_id char(32) NOT NULL,
                user_id char(32) NOT NULL,
                transaction_type varchar(10) NOT NULL,
                quantity integer unsigned NOT NULL,
                timestamp datetime NOT NULL,
                notes TEXT NOT NULL,
                reference_number varchar(20) NULL,
                region_id char(32) NULL
            );
            INSERT INTO api_transaction_old SELECT 
                id, branch_id, item_id, user_id, transaction_type, 
                quantity, timestamp, notes, reference_number, NULL as region_id
            FROM api_transaction;
            DROP TABLE api_transaction;
            ALTER TABLE api_transaction_old RENAME TO api_transaction;
            """
        ),
    ] 