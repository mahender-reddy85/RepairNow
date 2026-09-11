from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages
from django.contrib.auth import REDIRECT_FIELD_NAME

def customer_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect(f"/login/?next={request.path}")
        if not (request.user.is_customer or request.user.is_admin_user):
            messages.error(request, "Access restricted to Customer accounts.")
            return redirect('technician_dashboard')
        return view_func(request, *args, **kwargs)
    return _wrapped_view

def technician_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect(f"/login/?next={request.path}")
        if not (request.user.is_technician or request.user.is_admin_user):
            messages.error(request, "Access restricted to Technician accounts.")
            return redirect('customer_dashboard')
        return view_func(request, *args, **kwargs)
    return _wrapped_view

def admin_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect(f"/login/?next={request.path}")
        if not request.user.is_admin_user:
            messages.error(request, "Access restricted to Administrators.")
            if request.user.is_customer:
                return redirect('customer_dashboard')
            return redirect('technician_dashboard')
        return view_func(request, *args, **kwargs)
    return _wrapped_view
