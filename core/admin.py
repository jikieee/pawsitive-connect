from django.contrib import admin
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

# Import from correct apps
from accounts.models import UserProfile, SavedAnimal, AdoptionInquiry, Message, Notification, Conversation
from organizations.models import RescueOrganization, Announcement
from reports.models import AnimalReport, AnimalReportPhoto
from animals.models import RescuedAnimal, RescuedAnimalPhoto


# Register your models here
#admin.site.register(UserProfile)
#admin.site.register(RescueOrganization)
#admin.site.register(AnimalReport)
#admin.site.register(AnimalReportPhoto)dmin.site.register(RescuedAnimal)
#admin.site.register(RescuedAnimalPhoto)
#admin.site.register(SavedAnimal)
#admin.site.register(AdoptionInquiry)
#admin.site.register(Message)
#admin.site.register(Notification)
#admin.site.register(Announcement)
#admin.site.register(Conversation)


# ══════════════════════════════════════════════════
#  USER PROFILE - MAIN ADMIN INTERFACE
# ══════════════════════════════════════════════════

class UserProfileInline(admin.StackedInline):
    """Inline UserProfile editor in User admin."""
    model = UserProfile
    fields = ('role', 'phone', 'address', 'avatar', 'organization')
    extra = 0
    
    def get_queryset(self, request):
        # Ensure every user has a profile
        qs = super().get_queryset(request)
        for user in User.objects.all():
            UserProfile.objects.get_or_create(user=user)
        return qs


class CustomUserAdmin(BaseUserAdmin):
    """Extended User admin with UserProfile inline."""
    inlines = [UserProfileInline]


# Unregister default and register custom
admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)


# ══════════════════════════════════════════════════
#  ANIMAL REPORT & PHOTOS
# ══════════════════════════════════════════════════

class AnimalReportPhotoInline(admin.TabularInline):
    model = AnimalReportPhoto
    extra = 1
    fields = ('image', 'uploaded_at')
    readonly_fields = ('uploaded_at',)


class AnimalReportAdmin(admin.ModelAdmin):
    list_display = ('id', 'animal_type', 'status', 'priority', 'reporter', 'rescue_org', 'reported_at')
    list_filter = ('status', 'priority', 'animal_type', 'reported_at')
    search_fields = ('animal_type', 'description', 'reporter__username')
    readonly_fields = ('reported_at', 'updated_at')
    inlines = [AnimalReportPhotoInline]
    
    fieldsets = (
        ('Report Details', {
            'fields': ('animal_type', 'condition', 'status', 'priority', 'description')
        }),
        ('Location', {
            'fields': ('location', 'latitude', 'longitude')
        }),
        ('Assignment', {
            'fields': ('reporter', 'rescue_org')
        }),
        ('Response', {
            'fields': ('response_notes',)
        }),
        ('Metadata', {
            'fields': ('reported_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        """Filter reports based on user role."""
        qs = super().get_queryset(request)
        if not request.user.is_superuser:
            profile = UserProfile.objects.filter(user=request.user).first()
            if profile and profile.role == 'rescue_org' and profile.organization:
                qs = qs.filter(rescue_org=profile.organization)
        return qs


admin.site.register(AnimalReport, AnimalReportAdmin)


# ══════════════════════════════════════════════════
#  RESCUED ANIMAL & PHOTOS
# ══════════════════════════════════════════════════

class RescuedAnimalPhotoInline(admin.TabularInline):
    model = RescuedAnimalPhoto
    extra = 1
    fields = ('image', 'is_primary', 'uploaded_at')
    readonly_fields = ('uploaded_at',)


class RescuedAnimalAdmin(admin.ModelAdmin):
    list_display = ('name', 'species', 'breed', 'status', 'adoption_open', 'rescue_org', 'rescued_at')
    list_filter = ('status', 'species', 'adoption_open', 'rescued_at')
    search_fields = ('name', 'species', 'breed', 'rescue_org__name')
    readonly_fields = ('rescued_at',)
    inlines = [RescuedAnimalPhotoInline]
    
    fieldsets = (
        ('Animal Info', {
            'fields': ('name', 'species', 'breed', 'sex', 'approx_age', 'color')
        }),
        ('Status', {
            'fields': ('status', 'vaccination', 'shelter', 'adoption_open')
        }),
        ('Medical', {
            'fields': ('medical_notes', 'temperament')
        }),
        ('Organization', {
            'fields': ('rescue_org', 'source_report')
        }),
        ('Metadata', {
            'fields': ('rescued_at',),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        """Filter animals based on user role."""
        qs = super().get_queryset(request)
        if not request.user.is_superuser:
            profile = UserProfile.objects.filter(user=request.user).first()
            if profile and profile.role == 'rescue_org' and profile.organization:
                qs = qs.filter(rescue_org=profile.organization)
        return qs


admin.site.register(RescuedAnimal, RescuedAnimalAdmin)


# ══════════════════════════════════════════════════
#  SAVED ANIMALS
# ══════════════════════════════════════════════════

class SavedAnimalAdmin(admin.ModelAdmin):
    list_display = ('user', 'animal', 'saved_at')
    list_filter = ('saved_at',)
    search_fields = ('user__username', 'animal__name')
    readonly_fields = ('saved_at',)


admin.site.register(SavedAnimal, SavedAnimalAdmin)


class ConversationAdmin(admin.ModelAdmin):
    list_display = ('id', 'subject', 'created_at')
    search_fields = ('subject',)
    readonly_fields = ('created_at', 'updated_at')


admin.site.register(Conversation, ConversationAdmin)


# ══════════════════════════════════════════════════
#  ADOPTION INQUIRY
# ══════════════════════════════════════════════════

class AdoptionInquiryAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'animal', 'status', 'rescue_org', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('user__username', 'animal__name', 'rescue_org__name')
    readonly_fields = ('created_at',)
    
    fieldsets = (
        ('Inquiry Details', {
            'fields': ('user', 'animal', 'rescue_org', 'status')
        }),
        ('Applicant Info', {
            'fields': ('living_situation', 'other_pets', 'message')
        }),
        ('Metadata', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )


admin.site.register(AdoptionInquiry, AdoptionInquiryAdmin)


# ══════════════════════════════════════════════════
#  MESSAGES
# ══════════════════════════════════════════════════

class MessageAdmin(admin.ModelAdmin):
    list_display = ('sender', 'recipient', 'subject', 'is_read', 'sent_at')
    list_filter = ('is_read', 'sent_at')
    search_fields = ('sender__username', 'recipient__username', 'subject', 'body')
    readonly_fields = ('sent_at',)
    
    fieldsets = (
        ('Message Details', {
            'fields': ('sender', 'recipient', 'subject', 'body')
        }),
        ('Context', {
            'fields': ('animal', 'report')
        }),
        ('Status', {
            'fields': ('is_read', 'sent_at')
        }),
    )


admin.site.register(Message, MessageAdmin)


# ══════════════════════════════════════════════════
#  NOTIFICATIONS
# ══════════════════════════════════════════════════

class NotificationAdmin(admin.ModelAdmin):
    list_display = ('recipient', 'type', 'title', 'is_read', 'created_at')
    list_filter = ('type', 'is_read', 'created_at')
    search_fields = ('recipient__username', 'title', 'body')
    readonly_fields = ('created_at',)
    
    fieldsets = (
        ('Notification', {
            'fields': ('recipient', 'type', 'title', 'body', 'is_read')
        }),
        ('Context', {
            'fields': ('report', 'animal', 'inquiry')
        }),
        ('Metadata', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )


admin.site.register(Notification, NotificationAdmin)


# ══════════════════════════════════════════════════
#  ANNOUNCEMENTS
# ══════════════════════════════════════════════════

class AnnouncementAdmin(admin.ModelAdmin):
    list_display = ('title', 'rescue_org', 'type', 'is_pinned', 'created_at')
    list_filter = ('type', 'is_pinned', 'created_at')
    search_fields = ('title', 'body', 'rescue_org__name')
    readonly_fields = ('created_at',)
    
    fieldsets = (
        ('Announcement', {
            'fields': ('rescue_org', 'posted_by', 'type', 'title', 'body', 'photo')
        }),
        ('Settings', {
            'fields': ('is_pinned',)
        }),
        ('Metadata', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )


admin.site.register(Announcement, AnnouncementAdmin)


# ══════════════════════════════════════════════════
#  ADMIN CUSTOMIZATION
# ══════════════════════════════════════════════════

admin.site.site_header = "🐾 Pawsitive Connect Admin"
admin.site.site_title = "Pawsitive Connect"
admin.site.index_title = "Welcome to Pawsitive Connect Administration"
