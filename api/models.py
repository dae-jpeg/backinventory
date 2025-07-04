from django.contrib.auth.models import AbstractUser
from django.db import models
from django.conf import settings
import qrcode
from io import BytesIO
from django.core.files import File
import uuid
from django.core.validators import RegexValidator
from django.core.exceptions import ValidationError
from django.utils import timezone
import barcode
from barcode.writer import ImageWriter
from django.utils.text import slugify

class Company(models.Model):
    """Represents a company, the top-level entity in the hierarchy."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=150, unique=True)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name='owned_companies',
        on_delete=models.PROTECT,
        help_text="The Developer who owns this company profile."
    )
    description = models.TextField(blank=True)
    logo = models.ImageField(upload_to='company_logos/', blank=True, null=True)
    contact_info = models.CharField(max_length=200, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    location = models.CharField(max_length=200, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Company"
        verbose_name_plural = "Companies"
        ordering = ['name']

    def __str__(self):
        return self.name

class Branch(models.Model):
    """Represents a branch or location within a company."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(Company, related_name='branches', on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Branch"
        verbose_name_plural = "Branches"
        unique_together = ('company', 'name')
        ordering = ['company', 'name']

    def __str__(self):
        return f"{self.name} ({self.company.name})"

class CustomUser(AbstractUser):
    """
    Represents a global user account. Roles and branch assignments are handled
    through the CompanyMembership model.
    """
    USER_LEVEL_CHOICES = [
        ('DEVELOPER', 'Developer'),
        ('MEMBER', 'Member'), 
    ]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    global_user_level = models.CharField(max_length=15, choices=USER_LEVEL_CHOICES, default='MEMBER')
    
    id_number = models.CharField(
        max_length=20,
        unique=True, # ID number should be globally unique now
        validators=[RegexValidator(regex='^[0-9]+$', message='ID number must contain only digits')],
        help_text='Required. Enter a unique ID number (digits only).',
        default='00000000'
    )
    department = models.CharField(max_length=100, blank=True)
    contact_number = models.CharField(max_length=20, blank=True)
    qr_code = models.ImageField(upload_to='user_qr_codes/', blank=True, null=True)
    login_token = models.UUIDField(default=uuid.uuid4, editable=False)
    date_joined = models.DateTimeField(default=timezone.now)

    REQUIRED_FIELDS = ['email', 'id_number']

    def save(self, *args, **kwargs):
        if not self.qr_code:
            self.generate_qr()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.username})"

    def generate_qr(self):
        qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_L, box_size=10, border=4)
        qr_data = f"login_token:{str(self.login_token)}"
        qr.add_data(qr_data)
        qr.make(fit=True)
        qr_image = qr.make_image(fill_color="black", back_color="white")
        stream = BytesIO()
        qr_image.save(stream, 'PNG')
        filename = f'user_qr_{self.username}.png'
        self.qr_code.save(filename, File(stream), save=False)

class CompanyMembership(models.Model):
    """Links a user to a company with a specific role and branch."""
    ROLE_CHOICES = [
        ('OWNER', 'Owner'),
        ('SUPERVISOR', 'Supervisor'),
        ('BRANCH_MANAGER', 'Branch Manager'),
        ('USER', 'User'),
    ]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='company_memberships')
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='members')
    role = models.CharField(max_length=15, choices=ROLE_CHOICES)
    branch = models.ForeignKey(Branch, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        unique_together = ('user', 'company')
        verbose_name = "Company Membership"
        verbose_name_plural = "Company Memberships"

    def clean(self):
        super().clean()
        if self.branch and self.branch.company != self.company:
            raise ValidationError({'branch': 'The assigned branch does not belong to the selected company.'})
        if self.role in ['BRANCH_MANAGER', 'USER'] and not self.branch:
            raise ValidationError({'branch': f'A {self.get_role_display()} must be assigned to a branch.'})
        if self.role == 'SUPERVISOR' and self.branch:
            raise ValidationError({'branch': 'A Supervisor cannot be assigned to a specific branch.'})

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.user.username} in {self.company.name} as {self.get_role_display()}'

class Category(models.Model):
    """Represents an item category, optionally scoped to a company or branch."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=50)
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='categories')
    branch = models.ForeignKey(Branch, on_delete=models.SET_NULL, null=True, blank=True, related_name='categories')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('company', 'name', 'branch')
        verbose_name = 'Category'
        verbose_name_plural = 'Categories'
        ordering = ['name']

    def __str__(self):
        return self.name

class Item(models.Model):
    CATEGORY_CHOICES = [('ELECTRONICS', 'Electronics'), ('ACCESSORIES', 'Accessories'), ('AUDIO', 'Audio'), ('OTHER', 'Other')]
    STATUS_CHOICES = [('AVAILABLE', 'Available'), ('LOW_STOCK', 'Low Stock'), ('OUT_OF_STOCK', 'Out of Stock'), ('MAINTENANCE', 'Under Maintenance'), ('RETIRED', 'Retired')]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name='items')
    item_id = models.CharField(max_length=50, unique=True, blank=True, null=True, help_text="Auto-generated unique item ID")
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    category = models.ForeignKey('Category', on_delete=models.SET_NULL, null=True, blank=True, related_name='items')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='AVAILABLE')
    qr_code = models.ImageField(upload_to='item_qr_codes/', blank=True, null=True)
    barcode = models.ImageField(upload_to='item_barcodes/', blank=True, null=True)
    barcode_number = models.CharField(max_length=50, blank=True, null=True, help_text="Barcode number (can be different from item_id)")
    stock_quantity = models.PositiveIntegerField(default=0)
    original_stock_quantity = models.PositiveIntegerField(default=0, help_text="Original stock quantity when item was created")
    minimum_stock = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='created_items')

    class Meta:
        unique_together = [['branch', 'barcode_number']]

    def __str__(self):
        return f"{self.name} ({self.item_id}) @ {self.branch.name}"

    def generate_item_id(self):
        """Generate a unique item ID based on branch and timestamp."""
        import datetime
        # Get the current count of items in this branch
        branch_item_count = Item.objects.filter(branch=self.branch).count() + 1
        
        # Format: BRANCH-YYYYMMDD-XXXX (e.g., BRANCH1-20250628-0001)
        date_str = datetime.datetime.now().strftime('%Y%m%d')
        branch_code = self.branch.name.replace(' ', '').upper()[:8]  # First 8 chars of branch name
        item_number = f"{branch_item_count:04d}"  # 4-digit zero-padded number
        
        return f"{branch_code}-{date_str}-{item_number}"

    # ... other item methods (is_low_stock, generate_qr, etc.) remain the same ...
    def is_low_stock(self): return self.stock_quantity <= self.minimum_stock and self.stock_quantity > 0
    def is_out_of_stock(self): return self.stock_quantity == 0
    def is_available(self): return self.stock_quantity > 0
    def can_withdraw(self, quantity=1): return self.stock_quantity >= quantity and self.status not in ['MAINTENANCE', 'RETIRED']
    
    def update_status_based_on_stock(self):
        if self.is_out_of_stock(): self.status = 'OUT_OF_STOCK'
        elif self.is_low_stock(): self.status = 'LOW_STOCK'
        else: self.status = 'AVAILABLE'

    def withdraw_stock(self, quantity=1):
        print(f"[DEBUG] Withdrawing {quantity} from item '{self.name}' (before: {self.stock_quantity})")
        if self.can_withdraw(quantity):
            self.stock_quantity -= quantity
            self.update_status_based_on_stock()
            print(f"[DEBUG] Withdraw successful. New stock: {self.stock_quantity}")
            return True
        print(f"[DEBUG] Withdraw failed. Not enough stock or item not available.")
        return False

    def return_stock(self, quantity=1):
        print(f"[DEBUG] Returning {quantity} to item '{self.name}' (current stock: {self.stock_quantity}, original: {self.original_stock_quantity})")
        
        # Check if returning would exceed original stock quantity
        if self.stock_quantity + quantity > self.original_stock_quantity:
            print(f"[DEBUG] Return failed. Would exceed original stock quantity of {self.original_stock_quantity}")
            return False
        
        self.stock_quantity += quantity
        self.update_status_based_on_stock()
        print(f"[DEBUG] Return successful. New stock: {self.stock_quantity}")
        return True

    def generate_qr(self):
        qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_L, box_size=10, border=4)
        qr.add_data(f"item:{self.id}")
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        buffer = BytesIO()
        img.save(buffer, "PNG")
        self.qr_code.save(f"{self.item_id}_qr.png", File(buffer), save=False)

    def generate_barcode(self):
        # Use barcode_number if provided, otherwise use item_id
        barcode_value = self.barcode_number if self.barcode_number else self.item_id
        if not barcode_value:
            return
            
        code128 = barcode.get_barcode_class('code128')
        writer = ImageWriter()
        options = {'write_text': True}  # Show the barcode value as text below the barcode
        barcode_img = code128(barcode_value, writer)
        buffer = BytesIO()
        barcode_img.write(buffer, options)
        self.barcode.save(f"{barcode_value}_barcode.png", File(buffer), save=False)

    def save(self, *args, **kwargs):
        # Generate item_id if not provided (for new items)
        if not self.item_id:
            self.item_id = self.generate_item_id()
        
        # Set original_stock_quantity on first creation
        if not self.pk:
            # If stock_quantity is 0, set original_stock_quantity to 0 but warn
            # If stock_quantity > 0, set original_stock_quantity to stock_quantity
            self.original_stock_quantity = self.stock_quantity
            if self.stock_quantity == 0:
                print(f"[WARNING] Item '{self.name}' created with 0 stock. Returns will not be possible until stock is added.")
        
        self.update_status_based_on_stock()
        if not self.qr_code:
            self.generate_qr()
        self.generate_barcode()
        super().save(*args, **kwargs)

class Transaction(models.Model):
    TRANSACTION_TYPES = [('WITHDRAW', 'Withdraw'), ('RETURN', 'Return')]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name='transactions')
    item = models.ForeignKey(Item, on_delete=models.CASCADE, related_name='transactions')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='transactions')
    transaction_type = models.CharField(max_length=10, choices=TRANSACTION_TYPES)
    quantity = models.PositiveIntegerField(default=1)
    timestamp = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True)
    reference_number = models.CharField(max_length=20, unique=True, blank=True, null=True, help_text="Unique reference number for this transaction")

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.transaction_type} - {self.item.name} by {self.user.username}"

    def save(self, *args, **kwargs):
        print(f"[DEBUG] Transaction.save called: type={self.transaction_type}, item={self.item}, quantity={self.quantity}")
        if not self.reference_number:
            # Generate a unique reference number (e.g., TRX20240601-UUID4-short)
            import uuid, datetime
            date_str = datetime.datetime.now().strftime('%Y%m%d')
            unique_part = str(uuid.uuid4())[:8]
            self.reference_number = f"TRX{date_str}-{unique_part}"
        if self._state.adding:  # Use Django's internal flag for new objects
            if self.transaction_type == 'WITHDRAW':
                print(f"[DEBUG] Processing withdrawal for item {self.item} (current stock: {self.item.stock_quantity})")
                if not self.item.withdraw_stock(self.quantity):
                    print(f"[DEBUG] Withdrawal failed for item {self.item}")
                    raise ValueError(f"Cannot withdraw {self.quantity} of {self.item.name}. Insufficient stock or item not available.")
            elif self.transaction_type == 'RETURN':
                print(f"[DEBUG] Processing return for item {self.item} (current stock: {self.item.stock_quantity})")
                if not self.item.return_stock(self.quantity):
                    print(f"[DEBUG] Return failed for item {self.item}")
                    raise ValueError(f"Cannot return {self.quantity} of {self.item.name}. Would exceed original stock quantity of {self.item.original_stock_quantity}.")
                print(f"[DEBUG] Return processed successfully for item {self.item}")
            self.item.save()
        super().save(*args, **kwargs)
