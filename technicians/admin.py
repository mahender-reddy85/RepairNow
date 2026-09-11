from django.contrib import admin
from .models import TechnicianProfile, TechnicianSkill, Availability

class TechnicianSkillInline(admin.TabularInline):
    model = TechnicianSkill
    extra = 1

class AvailabilityInline(admin.TabularInline):
    model = Availability
    extra = 0

@admin.register(TechnicianProfile)
class TechnicianProfileAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'user', 'phone', 'city', 'verification_status', 'availability_status', 'average_rating', 'total_completed_jobs')
    list_filter = ('verification_status', 'availability_status', 'city')
    search_fields = ('full_name', 'phone', 'user__username', 'service_area', 'city')
    inlines = [TechnicianSkillInline, AvailabilityInline]

@admin.register(TechnicianSkill)
class TechnicianSkillAdmin(admin.ModelAdmin):
    list_display = ('technician', 'service_category', 'created_at')
    list_filter = ('service_category',)

@admin.register(Availability)
class AvailabilityAdmin(admin.ModelAdmin):
    list_display = ('technician', 'day_of_week', 'start_time', 'end_time', 'is_available')
    list_filter = ('day_of_week', 'is_available')
