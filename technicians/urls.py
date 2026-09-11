from django.urls import path
from . import views

urlpatterns = [
    path('technician/dashboard/', views.technician_dashboard, name='technician_dashboard'),
    path('technician/profile/', views.technician_profile, name='technician_profile'),
    path('technician/availability/', views.technician_availability, name='technician_availability'),
    path('technician/availability/toggle-ajax/', views.toggle_availability_ajax, name='toggle_availability_ajax'),
    path('technician/requests/', views.technician_requests, name='technician_requests'),
    path('technician/requests/<int:request_id>/', views.technician_request_detail, name='technician_request_detail'),
    path('technician/requests/<int:request_id>/accept/', views.technician_accept_request, name='technician_accept_request'),
    path('technician/requests/<int:request_id>/reject/', views.technician_reject_request, name='technician_reject_request'),
    path('technician/jobs/', views.technician_jobs, name='technician_jobs'),
    path('technician/jobs/<int:job_id>/', views.technician_job_detail, name='technician_job_detail'),
    path('technician/jobs/<int:job_id>/status-update/', views.technician_update_job_status, name='technician_update_job_status'),
    path('technician/history/', views.technician_history, name='technician_history'),
    path('technician/reviews/', views.technician_reviews, name='technician_reviews'),
    path('technician/notifications/', views.technician_notifications, name='technician_notifications'),
]
