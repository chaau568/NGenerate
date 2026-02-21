from django.contrib import admin
from .models import Notification

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'task_name', 'status', 'is_read', 'created_at')
    list_filter = ('status', 'is_read', 'created_at')
    search_fields = ('user__email', 'task_name', 'message')
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('User & Task', {
            'fields': ('user', 'task_name', 'status', 'is_read')
        }),
        ('Relate To', {
            'description': 'Notification must relate to either a Session or a Novel.',
            'fields': ('session', 'novel')
        }),
        ('Details', {
            'fields': ('message', 'created_at', 'updated_at')
        }),
    )