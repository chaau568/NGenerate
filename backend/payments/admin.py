from django.contrib import admin
from .models import Package, Transaction, CreditLog

@admin.register(Package)
class PackageAdmin(admin.ModelAdmin):
    list_display = (
        'name', 
        'price', 
        'credits_limit', 
        'duration_days', 
        'is_active', 
        'create_at',
    )
    
    list_filter = ('is_active', 'create_at')
    search_fields = ('name',)
    ordering = ('-create_at',)
    
@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = (
        'user', 
        'package', 
        'credit_remaining', 
        'payment_status', 
        'start_at', 
        'expire_at', 
        'create_at',
    )
    
    list_filter = ('payment_status', 'package', 'create_at', )
    search_fields = ('user__username', 'user__email', 'payment_ref', )
    readonly_fields = ('create_at', 'update_at', 'credit_remaining', )
    
    fieldsets = (
        ('User Info', {'fields': ('user', 'package')}),
        ('Payment Status', {'fields': ('payment_status', 'payment_ref')}),
        ('Credit & Validity', {'fields': ('credit_remaining', 'start_at', 'expire_at')}),
        ('Timestamps', {'fields': ('create_at', 'update_at')}),
    )

@admin.register(CreditLog)
class CreditLogAdmin(admin.ModelAdmin):
    list_display = (
        'transaction', 
        'usage_type', 
        'credit_spend', 
        'create_at')
    
    list_filter = ('usage_type', 'create_at')
    search_fields = ('transaction__user__username', 'usage_type')
    readonly_fields = ('transaction', 'usage_type', 'credit_spend', 'create_at')

    def has_add_permission(self, request):
        return False