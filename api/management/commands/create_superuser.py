from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db import IntegrityError

User = get_user_model()

class Command(BaseCommand):
    help = 'Create a superuser if one does not exist'

    def handle(self, *args, **options):
        try:
            # Check if superuser already exists
            if User.objects.filter(is_superuser=True).exists():
                self.stdout.write(
                    self.style.SUCCESS('Superuser already exists')
                )
                return

            # Create superuser
            superuser = User.objects.create_superuser(
                username='admin',
                email='admin@example.com',
                password='admin123456'
            )
            
            self.stdout.write(
                self.style.SUCCESS(f'Successfully created superuser: {superuser.username}')
            )
            self.stdout.write(
                self.style.WARNING('Default password is: admin123456 - Change it after first login!')
            )
            
        except IntegrityError:
            self.stdout.write(
                self.style.SUCCESS('Superuser already exists')
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error creating superuser: {e}')
            ) 