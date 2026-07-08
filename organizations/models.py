from django.db import models
from django.contrib.auth.models import User

# ─────────────────────────────────────────────
#  RESCUE ORGANIZATION
# ─────────────────────────────────────────────

class RescueOrganization(models.Model):
    name          = models.CharField(max_length=200)
    contact_email = models.EmailField()
    contact_phone = models.CharField(max_length=20)
    address       = models.CharField(max_length=255)
    logo          = models.ImageField(upload_to='org_logos/', null=True, blank=True)
    description   = models.TextField(blank=True)
    is_active     = models.BooleanField(default=True)
    latitude      = models.FloatField(null=True, blank=True)
    longitude     = models.FloatField(null=True, blank=True)
    created_at    = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


# ─────────────────────────────────────────────
#  ANNOUNCEMENT  (posted by orgs)
# ─────────────────────────────────────────────

class Announcement(models.Model):
    TYPE_CHOICES = [
        ('update',   'Rescue Update'),
        ('urgent',   'Urgent Rescue Need'),
        ('adoption', 'Adoption Announcement'),
        ('missing',  'Missing Pet Alert'),
    ]

    rescue_org = models.ForeignKey(
        RescueOrganization, on_delete=models.CASCADE, related_name='announcements'
    )
    posted_by  = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, related_name='announcements'
    )
    type       = models.CharField(max_length=10, choices=TYPE_CHOICES)
    title      = models.CharField(max_length=255)
    body       = models.TextField()
    photo      = models.ImageField(upload_to='announcements/', null=True, blank=True)
    is_pinned  = models.BooleanField(default=False)
    is_active  = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"[{self.get_type_display()}] {self.title}"

    class Meta:
        ordering = ['-is_pinned', '-created_at']