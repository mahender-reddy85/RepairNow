from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError

class RepairRequest(models.Model):
    URGENCY_LOW = 'LOW'
    URGENCY_MEDIUM = 'MEDIUM'
    URGENCY_HIGH = 'HIGH'
    URGENCY_EMERGENCY = 'EMERGENCY'

    URGENCY_CHOICES = [
        (URGENCY_LOW, 'Low - Routine check / No hurry'),
        (URGENCY_MEDIUM, 'Medium - Within a couple of days'),
        (URGENCY_HIGH, 'High - Today or Tomorrow'),
        (URGENCY_EMERGENCY, 'Emergency - Immediate attention required'),
    ]

    STATUS_PENDING = 'PENDING'
    STATUS_MATCHING = 'MATCHING'
    STATUS_TECHNICIAN_SELECTED = 'TECHNICIAN_SELECTED'
    STATUS_ACCEPTED = 'ACCEPTED'
    STATUS_ON_THE_WAY = 'ON_THE_WAY'
    STATUS_ARRIVED = 'ARRIVED'
    STATUS_IN_PROGRESS = 'IN_PROGRESS'
    STATUS_COMPLETED = 'COMPLETED'
    STATUS_CANCELLED = 'CANCELLED'
    STATUS_REJECTED = 'REJECTED'
    STATUS_EXPIRED = 'EXPIRED'

    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pending'),
        (STATUS_MATCHING, 'Matching Technicians'),
        (STATUS_TECHNICIAN_SELECTED, 'Technician Selected'),
        (STATUS_ACCEPTED, 'Accepted by Technician'),
        (STATUS_ON_THE_WAY, 'Technician On The Way'),
        (STATUS_ARRIVED, 'Technician Arrived'),
        (STATUS_IN_PROGRESS, 'Repair In Progress'),
        (STATUS_COMPLETED, 'Repair Completed'),
        (STATUS_CANCELLED, 'Cancelled'),
        (STATUS_REJECTED, 'Rejected by Technician'),
        (STATUS_EXPIRED, 'Expired'),
    ]

    customer = models.ForeignKey('accounts.CustomerProfile', on_delete=models.CASCADE, related_name='repair_requests')
    service_category = models.ForeignKey('services.ServiceCategory', on_delete=models.PROTECT, related_name='repair_requests')
    device_name = models.CharField(max_length=150, help_text="e.g. Samsung Front Load Washer, Daikin 1.5T Inverter AC")
    problem_description = models.TextField(help_text="Describe the issue in detail")
    problem_image = models.ImageField(upload_to='repairs/', blank=True, null=True, help_text="Photo of device or defect")
    location = models.CharField(max_length=255, help_text="Street address / Landmark")
    city = models.CharField(max_length=100, default='Vijayawada')
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)

    urgency = models.CharField(max_length=20, choices=URGENCY_CHOICES, default=URGENCY_MEDIUM)
    preferred_date = models.DateField()
    preferred_time = models.CharField(max_length=50, default='Morning (9 AM - 12 PM)', help_text="Preferred time window")
    budget = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="Optional expected budget in INR")

    selected_technician = models.ForeignKey('technicians.TechnicianProfile', on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_requests')
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default=STATUS_PENDING)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def can_be_cancelled(self):
        return self.status in [self.STATUS_PENDING, self.STATUS_MATCHING, self.STATUS_TECHNICIAN_SELECTED]

    def __str__(self):
        return f"Req #{self.id}: {self.device_name} ({self.get_status_display()})"


class TechnicianMatch(models.Model):
    repair_request = models.ForeignKey(RepairRequest, on_delete=models.CASCADE, related_name='matches')
    technician = models.ForeignKey('technicians.TechnicianProfile', on_delete=models.CASCADE, related_name='matches')
    match_score = models.FloatField(help_text="Overall weighted match score (0 - 100)")
    skill_score = models.FloatField(default=0.0)
    availability_score = models.FloatField(default=0.0)
    distance_score = models.FloatField(default=0.0)
    rating_score = models.FloatField(default=0.0)
    cost_score = models.FloatField(default=0.0)
    distance = models.FloatField(default=0.0, help_text="Calculated approximate distance in km")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('repair_request', 'technician')
        ordering = ['-match_score', 'distance']

    def __str__(self):
        return f"Match: Tech {self.technician.full_name} for Req #{self.repair_request.id} - Score: {self.match_score}%"


class TechnicianRejection(models.Model):
    repair_request = models.ForeignKey(RepairRequest, on_delete=models.CASCADE, related_name='rejections')
    technician = models.ForeignKey('technicians.TechnicianProfile', on_delete=models.CASCADE, related_name='request_rejections')
    rejected_at = models.DateTimeField(auto_now_add=True)
    reason = models.TextField(blank=True)

    class Meta:
        ordering = ['-rejected_at']
        unique_together = ('repair_request', 'technician')

    def __str__(self):
        return f"Rejection: Tech {self.technician.full_name} for Req #{self.repair_request.id} at {self.rejected_at.strftime('%Y-%m-%d %H:%M')}"


class Job(models.Model):
    STATUS_ACCEPTED = 'ACCEPTED'
    STATUS_ON_THE_WAY = 'ON_THE_WAY'
    STATUS_ARRIVED = 'ARRIVED'
    STATUS_IN_PROGRESS = 'IN_PROGRESS'
    STATUS_COMPLETED = 'COMPLETED'
    STATUS_CANCELLED = 'CANCELLED'

    STATUS_CHOICES = [
        (STATUS_ACCEPTED, 'Accepted'),
        (STATUS_ON_THE_WAY, 'On The Way'),
        (STATUS_ARRIVED, 'Arrived at Location'),
        (STATUS_IN_PROGRESS, 'In Progress'),
        (STATUS_COMPLETED, 'Completed'),
        (STATUS_CANCELLED, 'Cancelled'),
    ]

    ALLOWED_TRANSITIONS = {
        STATUS_ACCEPTED: [STATUS_ON_THE_WAY, STATUS_CANCELLED],
        STATUS_ON_THE_WAY: [STATUS_ARRIVED, STATUS_CANCELLED],
        STATUS_ARRIVED: [STATUS_IN_PROGRESS, STATUS_CANCELLED],
        STATUS_IN_PROGRESS: [STATUS_COMPLETED, STATUS_CANCELLED],
        STATUS_COMPLETED: [],
        STATUS_CANCELLED: [],
    }

    repair_request = models.OneToOneField(RepairRequest, on_delete=models.CASCADE, related_name='job')
    technician = models.ForeignKey('technicians.TechnicianProfile', on_delete=models.CASCADE, related_name='jobs')
    customer = models.ForeignKey('accounts.CustomerProfile', on_delete=models.CASCADE, related_name='jobs')

    accepted_date = models.DateTimeField(auto_now_add=True)
    started_date = models.DateTimeField(null=True, blank=True)
    completed_date = models.DateTimeField(null=True, blank=True)
    final_cost = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="Final billable amount in INR")

    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default=STATUS_ACCEPTED)
    notes = models.TextField(blank=True, help_text="Job observations, parts replaced or work performed")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def transition_to(self, new_status, user, note=""):
        if new_status not in self.ALLOWED_TRANSITIONS.get(self.status, []):
            raise ValidationError(f"Invalid transition from {self.status} to {new_status}")

        self.status = new_status
        self.repair_request.status = new_status
        self.repair_request.save(update_fields=['status', 'updated_at'])

        if new_status == self.STATUS_IN_PROGRESS and not self.started_date:
            from django.utils import timezone
            self.started_date = timezone.now()
        elif new_status == self.STATUS_COMPLETED and not self.completed_date:
            from django.utils import timezone
            self.completed_date = timezone.now()
            self.technician.update_rating_stats()

        self.save()

        JobStatusHistory.objects.create(
            job=self,
            status=new_status,
            changed_by=user,
            note=note
        )

    def __str__(self):
        return f"Job #{self.id} (Req #{self.repair_request.id}): {self.get_status_display()}"


class JobStatusHistory(models.Model):
    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name='status_history')
    status = models.CharField(max_length=30)
    changed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    note = models.TextField(blank=True)

    class Meta:
        ordering = ['timestamp']

    def __str__(self):
        return f"Job #{self.job.id} -> {self.status} at {self.timestamp.strftime('%Y-%m-%d %H:%M')}"
