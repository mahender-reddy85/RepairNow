from django.urls import path
from . import views

urlpatterns = [
    path('customer/review/<int:job_id>/', views.submit_review, name='submit_review'),
    path('complaint/create/', views.submit_complaint, name='submit_complaint'),
    path('complaint/create/<int:job_id>/', views.submit_complaint, name='submit_complaint_job'),
]
