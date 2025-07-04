from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser, Item, Transaction, Company, Branch, CompanyMembership

class CompanyMembershipInline(admin.TabularInline):
    """Inline admin for CompanyMembership."""
    model = CompanyMembership
    extra = 1
    autocomplete_fields = ['user']

class CustomUserAdmin(UserAdmin):
    """Admin configuration for CustomUser."""
    model = CustomUser
    list_display = ('username', 'email', 'first_name', 'last_name', 'global_user_level', 'is_staff')
    list_filter = ('global_user_level', 'is_staff', 'is_superuser', 'groups')
    search_fields = ('username', 'first_name', 'last_name', 'email')
    ordering = ('username',)
    
    fieldsets = UserAdmin.fieldsets + (
        ('Custom Fields', {'fields': ('global_user_level', 'id_number', 'department', 'contact_number')}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Custom Fields', {'fields': ('global_user_level', 'id_number', 'department', 'contact_number')}),
    )

class BranchInline(admin.TabularInline):
    """Inline admin for Branch."""
    model = Branch
    extra = 1
    show_change_link = True

@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    """Admin configuration for Company."""
    list_display = ('name', 'owner', 'created_at')
    search_fields = ('name', 'owner__username')
    list_filter = ('created_at',)
    inlines = [BranchInline, CompanyMembershipInline]

@admin.register(Branch)
class BranchAdmin(admin.ModelAdmin):
    """Admin configuration for Branch."""
    list_display = ('name', 'company', 'is_active')
    search_fields = ('name', 'company__name')
    list_filter = ('company', 'is_active')

@admin.register(Item)
class ItemAdmin(admin.ModelAdmin):
    """Admin configuration for Item."""
    list_display = ('name', 'item_id', 'branch', 'status', 'stock_quantity')
    search_fields = ('name', 'item_id', 'branch__name')
    list_filter = ('status', 'branch__company', 'branch')
    readonly_fields = ('qr_code',)

@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    """Admin configuration for Transaction."""
    list_display = ('item', 'user', 'transaction_type', 'quantity', 'timestamp')
    search_fields = ('item__name', 'user__username')
    list_filter = ('transaction_type', 'timestamp', 'branch')

# Unregister the old UserAdmin if CustomUser is the primary user model
# and then register the new one.
# Note: The base User model is automatically registered by Django,
# so we only need to register our custom user admin.
admin.site.register(CustomUser, CustomUserAdmin)
admin.site.register(CompanyMembership)
