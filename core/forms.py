from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

# Import from correct apps
from accounts.models import UserProfile
from organizations.models import RescueOrganization

class ImageValidationMixin:
    allowed_content_types = {'image/jpeg', 'image/png', 'image/gif', 'image/webp'}

    def clean_image_field(self, field_name):
        image = self.cleaned_data.get(field_name)
        if image and hasattr(image, 'content_type'):
            if image.content_type not in self.allowed_content_types:
                raise forms.ValidationError('Upload a JPG, PNG, GIF, or WebP image.')
        return image


class RegistrationForm(UserCreationForm):
    first_name = forms.CharField(max_length=150, required=True)
    last_name = forms.CharField(max_length=150, required=False)
    email = forms.EmailField(required=True)
    phone = forms.CharField(max_length=20, required=False)
    address = forms.CharField(max_length=255, required=False)

    organization_name = forms.CharField(max_length=200, required=False)
    organization_phone = forms.CharField(max_length=20, required=False)
    organization_address = forms.CharField(max_length=255, required=False)
    organization_latitude = forms.FloatField(required=False, min_value=-90, max_value=90)
    organization_longitude = forms.FloatField(required=False, min_value=-180, max_value=180)
    organization_description = forms.CharField(widget=forms.Textarea, required=False)

    class Meta(UserCreationForm.Meta):
        model = User
        fields = (
            'username', 'first_name', 'last_name', 'email',
            'password1', 'password2',
        )

    def __init__(self, *args, selected_role='reporter', **kwargs):
        self.selected_role = selected_role
        super().__init__(*args, **kwargs)
        placeholders = {
            'username': 'Choose a username',
            'first_name': 'Your first name',
            'last_name': 'Your last name',
            'email': 'name@example.com',
            'phone': '09XXXXXXXXX',
            'address': 'City / barangay / street',
            'password1': 'Create a strong password',
            'password2': 'Re-enter your password',
            'organization_name': 'Official rescue organization name',
            'organization_phone': 'Organization contact number',
            'organization_address': 'Organization address or operating area',
            'organization_latitude': 'Latitude, e.g. 14.5995',
            'organization_longitude': 'Longitude, e.g. 120.9842',
            'organization_description': 'Short description of your rescue work',
        }
        for name, field in self.fields.items():
            css = field.widget.attrs.get('class', '')
            field.widget.attrs['class'] = (css + ' register-input').strip()
            if name in placeholders:
                field.widget.attrs.setdefault('placeholder', placeholders[name])
        self.fields['organization_description'].widget.attrs.update({'rows': 4})
        if selected_role == 'rescue_org':
            self.fields['organization_name'].required = True
            self.fields['organization_phone'].required = True
            self.fields['organization_address'].required = True

    def clean_email(self):
        email = self.cleaned_data['email'].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError('An account with this email already exists.')
        return email

    def clean(self):
        cleaned = super().clean()
        if self.selected_role == 'admin':
            raise forms.ValidationError('Admin accounts must be created by an existing administrator.')
        return cleaned

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data.get('last_name', '')
        if commit:
            user.save()
            organization = None
            if self.selected_role == 'rescue_org':
                organization = RescueOrganization.objects.create(
                    name=self.cleaned_data['organization_name'],
                    contact_email=user.email,
                    contact_phone=self.cleaned_data['organization_phone'],
                    address=self.cleaned_data['organization_address'],
                    latitude=self.cleaned_data.get('organization_latitude'),
                    longitude=self.cleaned_data.get('organization_longitude'),
                    description=self.cleaned_data.get('organization_description', ''),
                    is_active=True,
                )
            UserProfile.objects.update_or_create(
                user=user,
                defaults={
                    'role': self.selected_role,
                    'phone': self.cleaned_data.get('phone', ''),
                    'address': self.cleaned_data.get('address', ''),
                    'organization': organization,
                },
            )
        return user


class ProfileUpdateForm(ImageValidationMixin, forms.ModelForm):
    first_name = forms.CharField(max_length=150, required=True)
    last_name = forms.CharField(max_length=150, required=False)
    email = forms.EmailField(required=True)

    class Meta:
        model = UserProfile
        fields = ('phone', 'address', 'avatar')

    def __init__(self, *args, user=None, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)
        if user is not None:
            self.fields['first_name'].initial = user.first_name
            self.fields['last_name'].initial = user.last_name
            self.fields['email'].initial = user.email

    def clean_email(self):
        email = self.cleaned_data['email'].strip().lower()
        if User.objects.exclude(pk=self.user.pk).filter(email__iexact=email).exists():
            raise forms.ValidationError('Another account is already using this email.')
        return email

    def clean_avatar(self):
        return self.clean_image_field('avatar')

    def save(self, commit=True):
        profile = super().save(commit=False)
        if commit:
            profile.save()
            self.user.first_name = self.cleaned_data['first_name']
            self.user.last_name = self.cleaned_data.get('last_name', '')
            self.user.email = self.cleaned_data['email']
            self.user.save(update_fields=['first_name', 'last_name', 'email'])
        return profile
