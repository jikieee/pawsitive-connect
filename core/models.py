from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

from accounts.models import (
    AdoptionInquiry,
    Conversation,
    Message,
    Notification,
    SavedAnimal,
    UserProfile,
)
from animals.models import RescuedAnimal, RescuedAnimalPhoto
from organizations.models import Announcement, RescueOrganization
from reports.models import AnimalReport, AnimalReportPhoto

__all__ = [
    'User',
    'models',
    'timezone',
    'AdoptionInquiry',
    'Conversation',
    'Message',
    'Notification',
    'SavedAnimal',
    'UserProfile',
    'RescuedAnimal',
    'RescuedAnimalPhoto',
    'Announcement',
    'RescueOrganization',
    'AnimalReport',
    'AnimalReportPhoto',
    'AdminAuditLog',
]




class AdminAuditLog(models.Model):
    """Lightweight audit trail for administrator dashboard actions."""
    ACTION_CHOICES = [
        ('user_toggle', 'User Active Status Changed'),
        ('org_toggle', 'Organization Active Status Changed'),
        ('report_status', 'Report Status Updated'),
        ('export', 'CSV Exported'),
    ]

    actor = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='admin_audit_logs')
    action = models.CharField(max_length=30, choices=ACTION_CHOICES)
    target_label = models.CharField(max_length=255)
    details = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        actor_name = self.actor.username if self.actor else 'System'
        return f'{actor_name} · {self.get_action_display()} · {self.target_label}'
