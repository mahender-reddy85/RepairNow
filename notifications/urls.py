from django.urls import path
from . import views

urlpatterns = [
    path('notifications/<int:notif_id>/mark-read/', views.mark_notification_read, name='mark_notification_read'),
    path('notifications/mark-all-read/', views.mark_all_notifications_read, name='mark_all_notifications_read'),
    path('notifications/<int:notif_id>/delete/', views.delete_notification, name='delete_notification'),
]
