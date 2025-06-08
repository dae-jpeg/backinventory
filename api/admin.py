from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.html import format_html
from .models import CustomUser, Item, Transaction

@admin.register(CustomUser)
class CustomUserAdmin(admin.ModelAdmin):
    list_display = ('id_number', 'username', 'email', 'first_name', 'last_name', 'is_staff', 'qr_code_preview')
    search_fields = ('id_number', 'username', 'email', 'first_name', 'last_name')
    list_filter = ('is_staff', 'is_active', 'date_joined')

    def qr_code_preview(self, obj):
        if obj.qr_code:
            return format_html('<img src="{}" width="50" height="50" />', obj.qr_code.url)
        return "No QR Code"
    qr_code_preview.short_description = 'QR Code'

@admin.register(Item)
class ItemAdmin(admin.ModelAdmin):
    list_display = ('item_id', 'name', 'category', 'status', 'qr_code_preview', 'created_at')
    list_filter = ('category', 'status', 'created_at')
    search_fields = ('item_id', 'name', 'description')
    readonly_fields = ('qr_code_preview',)
    fieldsets = (
        (None, {
            'fields': ('item_id', 'name', 'description')
        }),
        ('Classification', {
            'fields': ('category', 'status')
        }),
        ('QR Code', {
            'fields': ('qr_code', 'qr_code_preview'),
        }),
    )

    def qr_code_preview(self, obj):
        if obj.qr_code:
            return format_html('<img src="{}" width="100" height="100" />', obj.qr_code.url)
        return "No QR Code"
    qr_code_preview.short_description = 'QR Code Preview'

@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ('timestamp', 'item_name', 'user_name', 'transaction_type')
    list_filter = ('transaction_type', 'timestamp', 'item__category')
    search_fields = ('item__name', 'item__item_id', 'user__username', 'user__id_number')
    date_hierarchy = 'timestamp'

    def item_name(self, obj):
        return f"{obj.item.item_id} - {obj.item.name}"
    item_name.short_description = 'Item'

    def user_name(self, obj):
        return f"{obj.user.id_number} - {obj.user.get_full_name()}"
    user_name.short_description = 'User'
