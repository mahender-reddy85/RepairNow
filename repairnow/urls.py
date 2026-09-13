from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from . import admin_views
from . import views

urlpatterns = [
    path('django-admin/', admin.site.urls),
    path('admin/', admin_views.admin_dashboard, name='admin_dashboard'),
    path('admin/dashboard/', admin_views.admin_dashboard),
    path('admin/users/', admin_views.admin_users, name='admin_users'),
    path('admin/users/<int:user_id>/toggle/', admin_views.admin_toggle_user_active, name='admin_toggle_user_active'),
    path('admin/technicians/', admin_views.admin_technicians, name='admin_technicians'),
    path('admin/verifications/', admin_views.admin_verifications, name='admin_verifications'),
    path('admin/technicians/<int:tech_id>/<str:action>/', admin_views.admin_verify_technician, name='admin_verify_technician'),
    path('admin/services/', admin_views.admin_services, name='admin_services'),
    path('admin/requests/', admin_views.admin_requests, name='admin_requests'),
    path('admin/reviews/', admin_views.admin_reviews, name='admin_reviews'),
    path('admin/complaints/', admin_views.admin_complaints, name='admin_complaints'),
    path('', include('services.urls')),
    path('', include('accounts.urls')),
    path('', include('technicians.urls')),
    path('', include('repairs.urls')),
    path('', include('reviews.urls')),
    path('', include('notifications.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

handler404 = 'repairnow.views.error_404'
handler403 = 'repairnow.views.error_403'
handler500 = 'repairnow.views.error_500'
