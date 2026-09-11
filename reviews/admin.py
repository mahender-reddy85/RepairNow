from django.contrib import admin
from .models import Review, Complaint


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('id', 'job', 'customer', 'technician', 'rating', 'created_at')
    list_filter = ('rating',)
    search_fields = ('customer__full_name', 'technician__full_name', 'comment')


@admin.register(Complaint)
class ComplaintAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'subject', 'status', 'created_at')
    list_filter = ('status',)
    search_fields = ('user__username', 'subject', 'description')
