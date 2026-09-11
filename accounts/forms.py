from django import forms
from django.contrib.auth import get_user_model
from .models import CustomerProfile
from technicians.models import TechnicianProfile, TechnicianSkill
from services.models import ServiceCategory

User = get_user_model()

class LoginForm(forms.Form):
    username = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter your username'})
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Enter your password'})
    )


class CustomerRegistrationForm(forms.ModelForm):
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Create password (min 6 characters)'}),
        min_length=6
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Re-enter password'}),
        min_length=6
    )
    full_name = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Full Name'}))
    phone = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Mobile Number (e.g. 9876543210)'}))
    address = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'House / Flat / Street Address'}))
    city = forms.CharField(initial='Vijayawada', widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'City'}))
    state = forms.CharField(initial='Andhra Pradesh', widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'State'}))
    postal_code = forms.CharField(required=False, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Pincode / Postal Code'}))

    class Meta:
        model = User
        fields = ['username', 'email']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Choose username'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email address'}),
        }

    def clean_phone(self):
        phone = self.cleaned_data.get('phone', '').strip()
        if not phone.isdigit() or len(phone) < 10:
            raise forms.ValidationError("Please enter a valid phone number (at least 10 digits).")
        return phone

    def clean(self):
        cleaned_data = super().clean()
        p1 = cleaned_data.get('password')
        p2 = cleaned_data.get('confirm_password')
        if p1 and p2 and p1 != p2:
            self.add_error('confirm_password', "Passwords do not match.")
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password'])
        user.role = User.ROLE_CUSTOMER
        user.phone = self.cleaned_data['phone']
        if commit:
            user.save()
            CustomerProfile.objects.create(
                user=user,
                full_name=self.cleaned_data['full_name'],
                phone=self.cleaned_data['phone'],
                address=self.cleaned_data['address'],
                city=self.cleaned_data['city'],
                state=self.cleaned_data['state'],
                postal_code=self.cleaned_data.get('postal_code', ''),
            )
        return user


class TechnicianRegistrationForm(forms.ModelForm):
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Create password (min 6 characters)'}),
        min_length=6
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Re-enter password'}),
        min_length=6
    )
    full_name = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Full Name'}))
    phone = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Mobile Number'}))
    experience = forms.IntegerField(min_value=0, initial=2, widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Years of experience'}))
    service_area = forms.CharField(initial='Vijayawada Central, Benz Circle', widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Operating areas / localities'}))
    address = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Workshop / Base Address'}))
    city = forms.CharField(initial='Vijayawada', widget=forms.TextInput(attrs={'class': 'form-control'}))
    bio = forms.CharField(required=False, widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Brief intro and experience summary'}))
    
    skills = forms.ModelMultipleChoiceField(
        queryset=ServiceCategory.objects.filter(is_active=True),
        widget=forms.CheckboxSelectMultiple(),
        help_text="Select all repair skills you specialize in"
    )

    estimated_cost_min = forms.DecimalField(initial=300.0, widget=forms.NumberInput(attrs={'class': 'form-control'}))
    estimated_cost_max = forms.DecimalField(initial=800.0, widget=forms.NumberInput(attrs={'class': 'form-control'}))
    verification_document = forms.FileField(required=False, widget=forms.FileInput(attrs={'class': 'form-control'}))

    class Meta:
        model = User
        fields = ['username', 'email']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Choose username'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email address'}),
        }

    def clean_phone(self):
        phone = self.cleaned_data.get('phone', '').strip()
        if not phone.isdigit() or len(phone) < 10:
            raise forms.ValidationError("Please enter a valid phone number (at least 10 digits).")
        return phone

    def clean(self):
        cleaned_data = super().clean()
        p1 = cleaned_data.get('password')
        p2 = cleaned_data.get('confirm_password')
        if p1 and p2 and p1 != p2:
            self.add_error('confirm_password', "Passwords do not match.")

        c_min = cleaned_data.get('estimated_cost_min')
        c_max = cleaned_data.get('estimated_cost_max')
        if c_min is not None and c_max is not None and c_min > c_max:
            self.add_error('estimated_cost_min', "Minimum cost cannot exceed maximum cost.")
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password'])
        user.role = User.ROLE_TECHNICIAN
        user.phone = self.cleaned_data['phone']
        if commit:
            user.save()
            profile = TechnicianProfile.objects.create(
                user=user,
                full_name=self.cleaned_data['full_name'],
                phone=self.cleaned_data['phone'],
                experience=self.cleaned_data['experience'],
                service_area=self.cleaned_data['service_area'],
                address=self.cleaned_data['address'],
                city=self.cleaned_data['city'],
                bio=self.cleaned_data.get('bio', ''),
                estimated_cost_min=self.cleaned_data['estimated_cost_min'],
                estimated_cost_max=self.cleaned_data['estimated_cost_max'],
                verification_document=self.cleaned_data.get('verification_document'),
                verification_status=TechnicianProfile.VERIFICATION_PENDING,
            )
            for cat in self.cleaned_data['skills']:
                TechnicianSkill.objects.create(technician=profile, service_category=cat)
        return user


class CustomerProfileUpdateForm(forms.ModelForm):
    class Meta:
        model = CustomerProfile
        fields = ['full_name', 'phone', 'address', 'city', 'state', 'postal_code', 'profile_image']
        widgets = {
            'full_name': forms.TextInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'address': forms.TextInput(attrs={'class': 'form-control'}),
            'city': forms.TextInput(attrs={'class': 'form-control'}),
            'state': forms.TextInput(attrs={'class': 'form-control'}),
            'postal_code': forms.TextInput(attrs={'class': 'form-control'}),
            'profile_image': forms.FileInput(attrs={'class': 'form-control'}),
        }


class TechnicianProfileUpdateForm(forms.ModelForm):
    skills = forms.ModelMultipleChoiceField(
        queryset=ServiceCategory.objects.filter(is_active=True),
        widget=forms.CheckboxSelectMultiple(),
        required=False
    )

    class Meta:
        model = TechnicianProfile
        fields = [
            'full_name', 'phone', 'bio', 'experience', 'service_area', 
            'address', 'city', 'state', 'postal_code', 
            'estimated_cost_min', 'estimated_cost_max', 
            'availability_status', 'profile_image', 'verification_document'
        ]
        widgets = {
            'full_name': forms.TextInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'bio': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'experience': forms.NumberInput(attrs={'class': 'form-control'}),
            'service_area': forms.TextInput(attrs={'class': 'form-control'}),
            'address': forms.TextInput(attrs={'class': 'form-control'}),
            'city': forms.TextInput(attrs={'class': 'form-control'}),
            'state': forms.TextInput(attrs={'class': 'form-control'}),
            'postal_code': forms.TextInput(attrs={'class': 'form-control'}),
            'estimated_cost_min': forms.NumberInput(attrs={'class': 'form-control'}),
            'estimated_cost_max': forms.NumberInput(attrs={'class': 'form-control'}),
            'availability_status': forms.Select(attrs={'class': 'form-select'}),
            'profile_image': forms.FileInput(attrs={'class': 'form-control'}),
            'verification_document': forms.FileInput(attrs={'class': 'form-control'}),
        }
