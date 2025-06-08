from django.contrib.auth.models import AbstractUser
from django.db import models
import qrcode
from io import BytesIO
from django.core.files import File
from PIL import Image
import uuid
from django.core.validators import RegexValidator
from django.utils import timezone

class CustomUser(AbstractUser):
    USER_LEVEL_CHOICES = [
        ('ADMIN', 'Admin'),
        ('STAFF', 'Staff'),
        ('USER', 'User'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    id_number = models.CharField(
        max_length=20,
        unique=True,
        validators=[
            RegexValidator(
                regex='^[0-9]+$',
                message='ID number must contain only digits',
            ),
        ],
        help_text='Required. Enter a unique ID number (digits only).',
        default='00000000'  # Default value for existing records
    )
    user_level = models.CharField(
        max_length=10,
        choices=USER_LEVEL_CHOICES,
        default='USER'
    )
    department = models.CharField(max_length=100, blank=True)
    contact_number = models.CharField(max_length=20, blank=True)
    qr_code = models.ImageField(upload_to='user_qr_codes/', blank=True, null=True)
    login_token = models.UUIDField(default=uuid.uuid4)
    date_joined = models.DateTimeField(default=timezone.now)

    USERNAME_FIELD = 'id_number'
    REQUIRED_FIELDS = ['email', 'username']

    def generate_qr(self):
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr_data = f"login_token:{str(self.login_token)}"
        qr.add_data(qr_data)
        qr.make(fit=True)
        qr_image = qr.make_image(fill_color="black", back_color="white")
        
        stream = BytesIO()
        qr_image.save(stream, 'PNG')
        filename = f'user_qr_{self.username}.png'
        self.qr_code.save(filename, File(stream), save=False)

    def save(self, *args, **kwargs):
        if not self.qr_code:
            self.generate_qr()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.username})"

class Item(models.Model):
    CATEGORY_CHOICES = [
        ('ELECTRONICS', 'Electronics'),
        ('ACCESSORIES', 'Accessories'),
        ('AUDIO', 'Audio'),
        ('OTHER', 'Other'),
    ]

    STATUS_CHOICES = [
        ('AVAILABLE', 'Available'),
        ('IN_USE', 'In Use'),
        ('MAINTENANCE', 'Under Maintenance'),
        ('RETIRED', 'Retired'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    item_id = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='OTHER')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='AVAILABLE')
    qr_code = models.ImageField(upload_to='item_qr_codes/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} ({self.item_id})"

    def generate_qr(self):
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(f"item:{self.id}")
        qr.make(fit=True)
        qr_image = qr.make_image(fill_color="black", back_color="white")
        
        stream = BytesIO()
        qr_image.save(stream, 'PNG')
        filename = f'item_qr_{self.item_id}.png'
        self.qr_code.save(filename, File(stream), save=False)

    def save(self, *args, **kwargs):
        if not self.qr_code:
            self.generate_qr()
        super().save(*args, **kwargs)

class Transaction(models.Model):
    TRANSACTION_TYPES = [
        ('WITHDRAW', 'Withdraw'),
        ('RETURN', 'Return'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    item = models.ForeignKey(Item, on_delete=models.CASCADE, related_name='transactions')
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='transactions')
    transaction_type = models.CharField(max_length=10, choices=TRANSACTION_TYPES)
    timestamp = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.transaction_type} - {self.item.name} by {self.user.first_name}"

    def save(self, *args, **kwargs):
        if self.transaction_type == 'WITHDRAW':
            self.item.status = 'IN_USE'
        elif self.transaction_type == 'RETURN':
            self.item.status = 'AVAILABLE'
        self.item.save()
        super().save(*args, **kwargs)
