from django.urls import path
from . import views

urlpatterns = [
    path('login/', views.custom_login, name='login'),
    path('logout/', views.custom_logout, name='logout'),
    path('register/customer/', views.register_customer, name='register_customer'),
    path('register/technician/', views.register_technician, name='register_technician'),
    path('redirect/', views.login_redirect, name='login_redirect'),
]
