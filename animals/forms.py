from django import forms
from .models import RescuedAnimal

class RescuedAnimalForm(forms.ModelForm):
    photos = forms.FileField(
        widget=forms.ClearableFileInput(attrs={'multiple': True}),
        required=False
    )

    class Meta:
        model = RescuedAnimal
        fields = [
            'name', 'species', 'sex', 'breed', 'approx_age', 'color',
            'status', 'vaccination', 'shelter', 'medical_notes',
            'temperament', 'adoption_open',
        ]

    def clean(self):
        cleaned = super().clean()
        if not cleaned.get('name'):
            self.add_error('name', 'Please provide an animal name or identifier.')
        return cleaned
