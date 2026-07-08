from django.db import models
from django.contrib.auth.models import User
from organizations.models import RescueOrganization

# ─────────────────────────────────────────────
#  ANIMAL REPORT  (submitted by users / reporters)
# ─────────────────────────────────────────────

class AnimalReport(models.Model):
    ANIMAL_TYPE_CHOICES = [
        ('dog',   'Dog'),
        ('cat',   'Cat'),
        ('other', 'Other'),
    ]
    CONDITION_CHOICES = [
        ('stray',     'Stray / Wandering'),
        ('injured',   'Injured'),
        ('sick',      'Sick / Ill'),
        ('abandoned', 'Abandoned'),
    ]
    # Full lifecycle: reporter → org flow
    STATUS_CHOICES = [
        ('pending',           'Pending'),
        ('responding',        'Responding'),
        ('rescued',           'Rescued'),
        ('under_observation', 'Under Observation'),
        ('in_treatment',      'Recovering'),
        ('ready_for_adoption','Ready for Adoption'),
        ('adopted',           'Adopted'),
        ('closed',            'Closed'),
    ]
    PRIORITY_CHOICES = [
        ('normal',   'Normal'),
        ('high',     'High Priority'),
        ('critical', 'Critical / Emergency'),
    ]

    reporter    = models.ForeignKey(
        User, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='reports'
    )
    rescue_org  = models.ForeignKey(
        RescueOrganization, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='assigned_reports'
    )

    animal_type = models.CharField(max_length=10, choices=ANIMAL_TYPE_CHOICES)
    condition   = models.CharField(max_length=20, choices=CONDITION_CHOICES)
    status      = models.CharField(max_length=25, choices=STATUS_CHOICES, default='pending')
    priority    = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='normal')

    description = models.TextField()
    location    = models.CharField(max_length=255)
    latitude    = models.FloatField(null=True, blank=True)
    longitude   = models.FloatField(null=True, blank=True)

    photo       = models.ImageField(upload_to='animal_photos/', null=True, blank=True)

    # Org's response notes (updated when org acts on this report)
    response_notes = models.TextField(blank=True)

    reported_at = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"#{self.pk} — {self.get_animal_type_display()} ({self.get_condition_display()}) @ {self.location}"

    def is_active(self):
        return self.status in ('pending', 'responding', 'rescued', 'under_observation', 'in_treatment')

    def status_step(self):
        """Return the real rescue-progress step for user-facing timelines.

        0 = submitted only
        1 = seen by organization
        2 = rescue team dispatched/responding
        3 = animal rescued
        4 = under recovery/treatment
        5 = completed/closed/adoption outcome
        """
        step_map = {
            'pending': 0,
            'responding': 2,
            'rescued': 3,
            'under_observation': 4,
            'in_treatment': 4,
            'ready_for_adoption': 5,
            'adopted': 5,
            'closed': 5,
        }
        return step_map.get(self.status, 0)

    def has_been_seen_by_org(self):
        """True once the organization has actually acted on the report."""
        return self.status != 'pending'

    class Meta:
        ordering = ['-reported_at']


# ─────────────────────────────────────────────
#  ANIMAL REPORT PHOTO  (multiple images per report)
# ─────────────────────────────────────────────

class AnimalReportPhoto(models.Model):
    report    = models.ForeignKey(AnimalReport, on_delete=models.CASCADE, related_name='photos')
    image     = models.ImageField(upload_to='report_photos/')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Photo for Report #{self.report_id}"