from django.urls import path
from . import views

urlpatterns = [
    path('customer/dashboard/', views.customer_dashboard, name='customer_dashboard'),
    path('customer/profile/', views.customer_profile, name='customer_profile'),
    path('customer/repair/create/', views.customer_repair_create, name='customer_repair_create'),
    path('customer/repair/list/', views.customer_repair_list, name='customer_repair_list'),
    path('customer/repair/<int:request_id>/', views.customer_repair_detail, name='customer_repair_detail'),
    path('customer/repair/<int:request_id>/matches/', views.customer_repair_matches, name='customer_repair_matches'),
    path('customer/repair/<int:request_id>/select/<int:tech_id>/', views.customer_select_technician, name='customer_select_technician'),
    path('customer/repair/<int:request_id>/track/', views.customer_repair_track, name='customer_repair_track'),
    path('customer/repair/<int:request_id>/status-api/', views.customer_repair_status_api, name='customer_repair_status_api'),
    path('customer/repair/<int:request_id>/cancel/', views.customer_repair_cancel, name='customer_repair_cancel'),
    path('customer/history/', views.customer_history, name='customer_history'),
    path('customer/notifications/', views.customer_notifications, name='customer_notifications'),
]
