from django.core.management.base import BaseCommand
from django.db import connections
from django.db.utils import OperationalError
import psycopg2

class Command(BaseCommand):
    help = 'Tests database connection'

    def handle(self, *args, **options):
        self.stdout.write('Testing database connection...')
        
        try:
            # Try Django's connection
            db_conn = connections['default']
            db_conn.cursor()
            self.stdout.write(self.style.SUCCESS('Django database connection successful!'))
            
            # Try direct psycopg2 connection
            conn = psycopg2.connect(
                dbname="qrinventory",
                user="postgres",
                password="daehx143",
                host="localhost",
                port="5432"
            )
            self.stdout.write(self.style.SUCCESS('Direct PostgreSQL connection successful!'))
            conn.close()
            
        except OperationalError as e:
            self.stdout.write(self.style.ERROR(f'Django database connection failed: {e}'))
        except psycopg2.Error as e:
            self.stdout.write(self.style.ERROR(f'PostgreSQL connection failed: {e}'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Unexpected error: {e}')) 