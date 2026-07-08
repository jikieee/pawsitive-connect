from django import forms
from .models import AdoptionInquiry, Message

class AdoptionInquiryForm(forms.ModelForm):
    class Meta:
        model = AdoptionInquiry
        fields = ['living_situation', 'other_pets', 'message']

    def clean_message(self):
        message = self.cleaned_data.get('message', '').strip()
        if not message:
            raise forms.ValidationError('Please include a message with your inquiry.')
        return message

class MessageForm(forms.ModelForm):
    class Meta:
        model = Message
        fields = ['subject', 'body']

    def clean_body(self):
        body = self.cleaned_data.get('body', '').strip()
        if not body:
            raise forms.ValidationError('Message body cannot be empty.')
        return body
