from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError

class Review(models.Model):
    job = models.OneToOneField('repairs.Job', on_delete=models.CASCADE, related_name='review')
    customer = models.ForeignKey('accounts.CustomerProfile', on_delete=models.CASCADE, related_name='reviews')
    technician = models.ForeignKey('technicians.TechnicianProfile', on_delete=models.CASCADE, related_name='reviews')
    rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="Rating must be between 1 and 5 stars"
    )
    comment = models.TextField(help_text="Detailed feedback about the service provided")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def clean(self):
        super().clean()
        try:
            job = getattr(self, 'job', None)
        except Exception:
            job = None

        if job:
            if job.status != 'COMPLETED':
                raise ValidationError("A review can only be submitted for a completed job.")
            if hasattr(self, 'customer') and self.customer_id and self.customer != job.customer:
                raise ValidationError("You can only review jobs initiated by yourself.")
            if hasattr(self, 'technician') and self.technician_id and self.technician != job.technician:
                raise ValidationError("Technician mismatch for this job.")

    def save(self, *args, **kwargs):
        if self.job and self.job.status != 'COMPLETED':
            raise ValidationError("A review can only be submitted for a completed job.")
        super().save(*args, **kwargs)
        self.technician.update_rating_stats()

    def __str__(self):
        return f"Review for {self.technician.full_name}: {self.rating} Stars by {self.customer.full_name}"


class Complaint(models.Model):
    STATUS_OPEN = 'OPEN'
    STATUS_IN_REVIEW = 'IN_REVIEW'
    STATUS_RESOLVED = 'RESOLVED'
    STATUS_REJECTED = 'REJECTED'

    STATUS_CHOICES = [
        (STATUS_OPEN, 'Open'),
        (STATUS_IN_REVIEW, 'In Review'),
        (STATUS_RESOLVED, 'Resolved'),
        (STATUS_REJECTED, 'Rejected'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='complaints')
    job = models.ForeignKey('repairs.Job', on_delete=models.SET_NULL, null=True, blank=True, related_name='complaints')
    subject = models.CharField(max_length=200)
    description = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_OPEN)
    admin_response = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Complaint #{self.id}: {self.subject} ({self.get_status_display()})"
