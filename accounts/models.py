from django.db import models
from django.contrib.auth.models import AbstractUser

class User(AbstractUser):
    ROLE_CUSTOMER = 'CUSTOMER'
    ROLE_TECHNICIAN = 'TECHNICIAN'
    ROLE_ADMIN = 'ADMIN'

    ROLE_CHOICES = [
        (ROLE_CUSTOMER, 'Customer'),
        (ROLE_TECHNICIAN, 'Technician'),
        (ROLE_ADMIN, 'Administrator'),
    ]

    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default=ROLE_CUSTOMER)
    phone = models.CharField(max_length=20, blank=True)

    @property
    def is_customer(self):
        return self.role == self.ROLE_CUSTOMER

    @property
    def is_technician(self):
        return self.role == self.ROLE_TECHNICIAN

    @property
    def is_admin_user(self):
        return self.role == self.ROLE_ADMIN or self.is_superuser or self.is_staff

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"


class CustomerProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='customer_profile')
    full_name = models.CharField(max_length=150)
    phone = models.CharField(max_length=20)
    address = models.TextField(blank=True)
    city = models.CharField(max_length=100, default='Vijayawada')
    state = models.CharField(max_length=100, default='Andhra Pradesh')
    postal_code = models.CharField(max_length=20, blank=True)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    profile_image = models.ImageField(upload_to='customers/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Customer: {self.full_name} ({self.user.username})"
