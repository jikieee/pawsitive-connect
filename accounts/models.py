from django.db import models
from django.contrib.auth.models import User
from organizations.models import RescueOrganization
from animals.models import RescuedAnimal

# ─────────────────────────────────────────────
#  USER PROFILE  (extends Django's built-in User)
# ─────────────────────────────────────────────

class UserProfile(models.Model):
    ROLE_CHOICES = [
        ('reporter',   'Reporter'),
        ('rescue_org', 'Rescue Organization'),
        ('admin',      'Admin'),
    ]
    user         = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role         = models.CharField(max_length=20, choices=ROLE_CHOICES, default='reporter')
    phone        = models.CharField(max_length=20, blank=True)
    address      = models.CharField(max_length=255, blank=True)
    avatar       = models.ImageField(upload_to='avatars/', null=True, blank=True)
    organization = models.ForeignKey(
        RescueOrganization, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='members'
    )

    def __str__(self):
        return f"{self.user.username} ({self.role})"

    def is_org_member(self):
        return self.role == 'rescue_org' and self.organization is not None

    def is_admin(self):
        return self.role == 'admin'

    def is_reporter(self):
        return self.role == 'reporter'


# ─────────────────────────────────────────────
#  SAVED ANIMAL  (users bookmark animals they like)
# ─────────────────────────────────────────────

class SavedAnimal(models.Model):
    user     = models.ForeignKey(User, on_delete=models.CASCADE, related_name='saved_animals')
    animal   = models.ForeignKey(RescuedAnimal, on_delete=models.CASCADE, related_name='saved_by')
    saved_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'animal')
        ordering = ['-saved_at']

    def __str__(self):
        return f"{self.user.username} saved {self.animal.display_name()}"

# ─────────────────────────────────────────────
#  ADOPTION INQUIRY  (user → org interest form)
# ─────────────────────────────────────────────

class AdoptionInquiry(models.Model):
    STATUS_CHOICES = [
        ('pending',  'Awaiting Reply'),
        ('replied',  'Replied'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('closed',   'Closed'),
    ]
    LIVING_CHOICES = [
        ('house',      'House with yard'),
        ('condo',      'Condo / Apartment'),
        ('townhouse',  'Townhouse'),
        ('other',      'Other'),
    ]
    PET_CHOICES = [
        ('none',     'No other pets'),
        ('dogs',     'Yes — dogs'),
        ('cats',     'Yes — cats'),
        ('multiple', 'Yes — multiple'),
    ]

    user           = models.ForeignKey(User, on_delete=models.CASCADE, related_name='adoption_inquiries')
    animal         = models.ForeignKey(RescuedAnimal, on_delete=models.CASCADE, related_name='inquiries')
    rescue_org     = models.ForeignKey(RescueOrganization, on_delete=models.CASCADE, related_name='inquiries')

    living_situation = models.CharField(max_length=20, choices=LIVING_CHOICES, default='house')
    other_pets       = models.CharField(max_length=20, choices=PET_CHOICES, default='none')
    message          = models.TextField()

    status     = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username} → {self.animal.display_name()} ({self.get_status_display()})"

    class Meta:
        ordering = ['-created_at']
        # Prevent duplicate inquiries for the same animal
        unique_together = ('user', 'animal')



# ─────────────────────────────────────────────
#  CONVERSATION / THREAD
# ─────────────────────────────────────────────

class Conversation(models.Model):
    subject = models.CharField(max_length=255, blank=True)
    inquiry = models.ForeignKey(
        'AdoptionInquiry', on_delete=models.CASCADE, related_name='conversations',
        null=True, blank=True,
    )
    participants = models.ManyToManyField(User, related_name='conversations')
    last_message = models.ForeignKey(
        'Message', on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.subject or f'Conversation {self.pk}'

class Message(models.Model):
    sender    = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_messages')
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_messages')

    conversation = models.ForeignKey(
        'Conversation', on_delete=models.CASCADE,
        null=True, blank=True, related_name='messages'
    )
    inquiry = models.ForeignKey(
        'AdoptionInquiry', on_delete=models.CASCADE,
        null=True, blank=True, related_name='messages'
    )

    # Use string references to avoid circular imports
    animal    = models.ForeignKey(
        'animals.RescuedAnimal', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='messages'
    )
    report    = models.ForeignKey(
        'reports.AnimalReport', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='messages'
    )

    subject   = models.CharField(max_length=255, blank=True)
    body      = models.TextField()
    is_read   = models.BooleanField(default=False)
    sent_at   = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"From {self.sender.username} → {self.recipient.username}: {self.subject or '(no subject)'}"

    class Meta:
        ordering = ['-sent_at']



# ─────────────────────────────────────────────
#  NOTIFICATION
# ─────────────────────────────────────────────

class Notification(models.Model):
    TYPE_CHOICES = [
        ('rescue_update', 'Rescue Update'),
        ('org_reply',     'Organization Reply'),
        ('new_user_message', 'New User Message'),
        ('adoption_ready','Adoption Ready'),
        ('report_seen',   'Report Seen'),
        ('report_closed', 'Report Closed'),
        ('new_inquiry',   'New Inquiry'),
        ('new_report',    'New Report'),
        ('inquiry_status_updated', 'Inquiry Status Updated'),
    ]

    recipient  = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    type       = models.CharField(max_length=30, choices=TYPE_CHOICES)
    title      = models.CharField(max_length=255)
    body       = models.TextField(blank=True)
    is_read    = models.BooleanField(default=False)

    # Use string references to prevent circular imports
    report     = models.ForeignKey(
        'reports.AnimalReport', 
        on_delete=models.SET_NULL, 
        null=True, blank=True
    )
    animal     = models.ForeignKey(
        'animals.RescuedAnimal', 
        on_delete=models.SET_NULL, 
        null=True, blank=True
    )
    inquiry    = models.ForeignKey(
        'accounts.AdoptionInquiry', 
        on_delete=models.SET_NULL, 
        null=True, blank=True
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"[{self.type}] → {self.recipient.username}: {self.title}"

    class Meta:
        ordering = ['-created_at']