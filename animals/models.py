from django.db import models
from django.utils import timezone
from organizations.models import RescueOrganization
from reports.models import AnimalReport   # if needed for source_report

# ─────────────────────────────────────────────
#  RESCUED ANIMAL  (created / managed by orgs)
# ─────────────────────────────────────────────

class RescuedAnimal(models.Model):
    SPECIES_CHOICES = [
        ('dog',   'Dog'),
        ('cat',   'Cat'),
        ('other', 'Other'),
    ]
    SEX_CHOICES = [
        ('male',    'Male'),
        ('female',  'Female'),
        ('unknown', 'Unknown'),
    ]
    STATUS_CHOICES = [
        ('observation', 'Under Observation'),
        ('recovering',  'Recovering'),
        ('adoption',    'Ready for Adoption'),
        ('adopted',     'Adopted'),
    ]
    VACCINATION_CHOICES = [
        ('none',    'Not Vaccinated'),
        ('partial', 'Partial'),
        ('complete','Fully Vaccinated'),
    ]

    rescue_org    = models.ForeignKey(
        RescueOrganization, on_delete=models.SET_NULL,
        null=True, related_name='rescued_animals'
    )
    source_report = models.OneToOneField(
        AnimalReport, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='rescued_animal'
    )

    name         = models.CharField(max_length=100, blank=True, help_text="Shelter name given to the animal")
    species      = models.CharField(max_length=10, choices=SPECIES_CHOICES)
    breed        = models.CharField(max_length=100, blank=True)
    sex          = models.CharField(max_length=10, choices=SEX_CHOICES, default='unknown')
    approx_age   = models.CharField(max_length=30, blank=True, help_text="e.g. ~2 yrs, 6 months")
    color        = models.CharField(max_length=100, blank=True)

    status       = models.CharField(max_length=15, choices=STATUS_CHOICES, default='observation')
    vaccination  = models.CharField(max_length=10, choices=VACCINATION_CHOICES, default='none')
    shelter      = models.CharField(max_length=100, blank=True, help_text="Shelter / kennel location")

    medical_notes   = models.TextField(blank=True)
    temperament     = models.CharField(max_length=255, blank=True, help_text="e.g. Gentle, Playful, Shy")
    adoption_open   = models.BooleanField(default=False, help_text="Toggle to show in adoption listings")

    rescued_at  = models.DateTimeField(default=timezone.now)
    updated_at  = models.DateTimeField(auto_now=True)

    def __str__(self):
        label = self.name if self.name else f"Unnamed {self.get_species_display()}"
        return f"{label} [{self.get_status_display()}]"

    def display_name(self):
        return self.name if self.name else f"Unnamed {self.get_species_display()}"

    class Meta:
        ordering = ['-rescued_at']



class RescuedAnimalPhoto(models.Model):
    animal      = models.ForeignKey(RescuedAnimal, on_delete=models.CASCADE, related_name='photos')
    image       = models.ImageField(upload_to='rescued_animal_photos/')
    is_primary  = models.BooleanField(default=False)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Photo for {self.animal.display_name()}"