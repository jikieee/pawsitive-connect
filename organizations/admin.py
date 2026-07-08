from django.contrib import admin

from .models import RescueOrganization


class RescueOrganizationAdmin(admin.ModelAdmin):
    list_display = ('name', 'contact_email', 'contact_phone', 'is_active', 'created_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('name', 'contact_email')
    readonly_fields = ('created_at',)

    fieldsets = (
        ('Organization Info', {
            'fields': ('name', 'description', 'address', 'latitude', 'longitude')
        }),
        ('Contact Details', {
            'fields': ('contact_email', 'contact_phone')
        }),
        ('Media & Status', {
            'fields': ('logo', 'is_active')
        }),
        ('Metadata', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )


admin.site.register(RescueOrganization, RescueOrganizationAdmin)
