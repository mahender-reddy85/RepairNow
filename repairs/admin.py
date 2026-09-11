from django.contrib import admin
from .models import RepairRequest, TechnicianMatch, Job, JobStatusHistory


class JobStatusHistoryInline(admin.TabularInline):
    model = JobStatusHistory
    extra = 0
    readonly_fields = ('status', 'changed_by', 'timestamp', 'note')


@admin.register(RepairRequest)
class RepairRequestAdmin(admin.ModelAdmin):
    list_display = ('id', 'device_name', 'customer', 'service_category', 'urgency', 'status', 'preferred_date', 'created_at')
    list_filter = ('status', 'urgency', 'service_category', 'city')
    search_fields = ('device_name', 'problem_description', 'customer__full_name', 'city')


@admin.register(TechnicianMatch)
class TechnicianMatchAdmin(admin.ModelAdmin):
    list_display = ('repair_request', 'technician', 'match_score', 'distance', 'created_at')
    list_filter = ('match_score',)


@admin.register(Job)
class JobAdmin(admin.ModelAdmin):
    list_display = ('id', 'repair_request', 'technician', 'customer', 'status', 'final_cost', 'created_at')
    list_filter = ('status',)
    inlines = [JobStatusHistoryInline]


@admin.register(JobStatusHistory)
class JobStatusHistoryAdmin(admin.ModelAdmin):
    list_display = ('job', 'status', 'changed_by', 'timestamp')
