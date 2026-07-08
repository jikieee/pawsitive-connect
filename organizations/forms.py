from django import forms
from .models import RescueOrganization

class RescueOrganizationForm(forms.ModelForm):
    class Meta:
        model = RescueOrganization
        fields = [
            'name', 'contact_email', 'contact_phone',
            'address', 'description', 'logo', 'is_active',
        ]
