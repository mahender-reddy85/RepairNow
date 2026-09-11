from django.db import models
from django.conf import settings

class TechnicianProfile(models.Model):
    VERIFICATION_PENDING = 'PENDING'
    VERIFICATION_VERIFIED = 'VERIFIED'
    VERIFICATION_REJECTED = 'REJECTED'
    VERIFICATION_SUSPENDED = 'SUSPENDED'

    VERIFICATION_CHOICES = [
        (VERIFICATION_PENDING, 'Pending Verification'),
        (VERIFICATION_VERIFIED, 'Verified'),
        (VERIFICATION_REJECTED, 'Rejected'),
        (VERIFICATION_SUSPENDED, 'Suspended'),
    ]

    AVAILABILITY_AVAILABLE = 'AVAILABLE'
    AVAILABILITY_BUSY = 'BUSY'
    AVAILABILITY_OFFLINE = 'OFFLINE'

    AVAILABILITY_CHOICES = [
        (AVAILABILITY_AVAILABLE, 'Available'),
        (AVAILABILITY_BUSY, 'Busy'),
        (AVAILABILITY_OFFLINE, 'Offline'),
    ]

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='technician_profile')
    full_name = models.CharField(max_length=150)
    phone = models.CharField(max_length=20)
    profile_image = models.ImageField(upload_to='technicians/', blank=True, null=True)
    bio = models.TextField(blank=True)
    experience = models.PositiveIntegerField(default=2, help_text="Years of professional repair experience")
    service_area = models.CharField(max_length=255, default='Vijayawada Metro', help_text="Operational zones or coverage areas")
    address = models.TextField(blank=True)
    city = models.CharField(max_length=100, default='Vijayawada')
    state = models.CharField(max_length=100, default='Andhra Pradesh')
    postal_code = models.CharField(max_length=20, blank=True)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    
    estimated_cost_min = models.DecimalField(max_digits=10, decimal_places=2, default=300.00)
    estimated_cost_max = models.DecimalField(max_digits=10, decimal_places=2, default=800.00)

    verification_status = models.CharField(max_length=20, choices=VERIFICATION_CHOICES, default=VERIFICATION_PENDING)
    verification_document = models.FileField(upload_to='verification_docs/', blank=True, null=True)
    
    availability_status = models.CharField(max_length=20, choices=AVAILABILITY_CHOICES, default=AVAILABILITY_AVAILABLE)
    average_rating = models.FloatField(default=0.0)
    total_reviews_count = models.PositiveIntegerField(default=0)
    total_completed_jobs = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def is_verified(self):
        return self.verification_status == self.VERIFICATION_VERIFIED

    def update_rating_stats(self):
        from reviews.models import Review
        reviews = Review.objects.filter(technician=self)
        self.total_reviews_count = reviews.count()
        if self.total_reviews_count > 0:
            total_score = sum(r.rating for r in reviews)
            self.average_rating = round(total_score / self.total_reviews_count, 1)
        else:
            self.average_rating = 0.0
            
        from repairs.models import Job
        self.total_completed_jobs = Job.objects.filter(technician=self, status='COMPLETED').count()
        self.save(update_fields=['average_rating', 'total_reviews_count', 'total_completed_jobs'])

    def __str__(self):
        return f"Technician: {self.full_name} ({self.verification_status})"


class TechnicianSkill(models.Model):
    technician = models.ForeignKey(TechnicianProfile, on_delete=models.CASCADE, related_name='skills')
    service_category = models.ForeignKey('services.ServiceCategory', on_delete=models.CASCADE, related_name='technician_skills')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('technician', 'service_category')

    def __str__(self):
        return f"{self.technician.full_name} - {self.service_category.name}"


class Availability(models.Model):
    DAY_CHOICES = [
        (0, 'Monday'),
        (1, 'Tuesday'),
        (2, 'Wednesday'),
        (3, 'Thursday'),
        (4, 'Friday'),
        (5, 'Saturday'),
        (6, 'Sunday'),
    ]

    technician = models.ForeignKey(TechnicianProfile, on_delete=models.CASCADE, related_name='availability_schedule')
    day_of_week = models.IntegerField(choices=DAY_CHOICES)
    start_time = models.TimeField(default='09:00')
    end_time = models.TimeField(default='18:00')
    is_available = models.BooleanField(default=True)

    class Meta:
        unique_together = ('technician', 'day_of_week')
        ordering = ['day_of_week']

    def __str__(self):
        day_name = dict(self.DAY_CHOICES).get(self.day_of_week, str(self.day_of_week))
        status = "Available" if self.is_available else "Not Available"
        return f"{self.technician.full_name}: {day_name} ({self.start_time}-{self.end_time}) [{status}]"
