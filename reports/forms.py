from django import forms
from .models import AnimalReport

class AnimalReportForm(forms.ModelForm):
    photo = forms.ImageField(required=False)
    latitude = forms.DecimalField(required=False, max_value=90, min_value=-90)
    longitude = forms.DecimalField(required=False, max_value=180, min_value=-180)

    class Meta:
        model = AnimalReport
        fields = [
            'animal_type', 'condition', 'priority',
            'description', 'location', 'latitude', 'longitude', 'photo',
        ]

    def clean(self):
        cleaned = super().clean()
        if not cleaned.get('description'):
            self.add_error('description', 'Describe the animal and situation.')
        if not cleaned.get('location'):
            self.add_error('location', 'Please provide a location.')
        return cleaned
