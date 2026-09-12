from django import forms
from django.utils import timezone
from .models import RepairRequest
from services.models import ServiceCategory


class RepairRequestForm(forms.ModelForm):
    preferred_date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        help_text="Select when you need the technician"
    )

    PREFERRED_TIME_CHOICES = [
        ('', 'Select preferred time'),
        ('Morning (8 AM - 12 PM)', 'Morning (8 AM - 12 PM)'),
        ('Afternoon (12 PM - 4 PM)', 'Afternoon (12 PM - 4 PM)'),
        ('Evening (4 PM - 8 PM)', 'Evening (4 PM - 8 PM)'),
    ]

    preferred_time = forms.ChoiceField(
        choices=PREFERRED_TIME_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'}),
    )

    class Meta:
        model = RepairRequest
        fields = [
            'service_category', 'device_name', 'problem_description',
            'problem_image', 'location', 'city', 'urgency',
            'preferred_date', 'preferred_time', 'budget'
        ]
        widgets = {
            'service_category': forms.Select(attrs={'class': 'form-select'}),
            'device_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Samsung 7kg Front-Load Washing Machine'}),
            'problem_description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Describe symptoms (e.g. not spinning, water leakage, strange noise)'}),
            'problem_image': forms.FileInput(attrs={'class': 'form-control'}),
            'location': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Door No, Apartment / Street, Landmark'}),
            'city': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'City'}),
            'urgency': forms.Select(attrs={'class': 'form-select'}),
            'budget': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Optional expected budget (₹)'}),
        }

    def clean_preferred_date(self):
        p_date = self.cleaned_data.get('preferred_date')
        if p_date and p_date < timezone.now().date():
            raise forms.ValidationError("Preferred date cannot be in the past.")
        return p_date

    def clean_budget(self):
        budget = self.cleaned_data.get('budget')
        if budget is not None and budget <= 0:
            raise forms.ValidationError("Budget must be a positive number.")
        return budget
