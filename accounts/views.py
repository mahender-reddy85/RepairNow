from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.utils.http import url_has_allowed_host_and_scheme
from django.core.cache import cache
from .forms import LoginForm, CustomerRegistrationForm, TechnicianRegistrationForm
from notifications.models import send_notification

MAX_FAILED_LOGIN_ATTEMPTS = 5
LOGIN_LOCKOUT_TIMEOUT = 300  # 5 minutes in seconds

def custom_login(request):
    if request.user.is_authenticated:
        return redirect('login_redirect')

    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']

            # Rate limiting check based on client IP and username
            client_ip = request.META.get('HTTP_X_FORWARDED_FOR', request.META.get('REMOTE_ADDR', '')).split(',')[0].strip()
            norm_username = username.strip().lower()
            lockout_key = f"login_lockout:{client_ip}:{norm_username}"
            attempts_key = f"login_attempts:{client_ip}:{norm_username}"

            if cache.get(lockout_key):
                messages.error(request, "Too many failed login attempts. Please try again later.")
                return render(request, 'accounts/login.html', {'form': form})

            user = authenticate(request, username=username, password=password)
            if user is not None:
                # Reset rate limiting counter upon successful authentication
                cache.delete(lockout_key)
                cache.delete(attempts_key)

                if user.is_active:
                    login(request, user)
                    messages.success(request, f"Welcome back, {user.username}!")
                    next_url = request.POST.get('next') or request.GET.get('next')
                    if next_url and url_has_allowed_host_and_scheme(url=next_url, allowed_hosts={request.get_host()}):
                        return redirect(next_url)
                    return redirect('login_redirect')
                else:
                    messages.error(request, "Your account is currently disabled. Please contact support.")
            else:
                attempts = cache.get(attempts_key, 0) + 1
                cache.set(attempts_key, attempts, timeout=LOGIN_LOCKOUT_TIMEOUT)
                if attempts >= MAX_FAILED_LOGIN_ATTEMPTS:
                    cache.set(lockout_key, True, timeout=LOGIN_LOCKOUT_TIMEOUT)
                    messages.error(request, "Too many failed login attempts. Please try again later.")
                else:
                    messages.error(request, "Invalid username or password.")
    else:
        form = LoginForm()

    return render(request, 'accounts/login.html', {'form': form})


@require_POST
def custom_logout(request):
    logout(request)
    messages.info(request, "You have been logged out successfully.")
    return redirect('home')


def register_customer(request):
    if request.user.is_authenticated:
        return redirect('login_redirect')

    if request.method == 'POST':
        form = CustomerRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            send_notification(
                user=user,
                title="Welcome to RepairNow!",
                message="Your customer account has been created. You can now request on-demand repair services.",
                link="/customer/dashboard/",
                notification_type="WELCOME"
            )
            login(request, user)
            messages.success(request, "Registration successful! Welcome to RepairNow.")
            return redirect('customer_dashboard')
    else:
        form = CustomerRegistrationForm()

    return render(request, 'accounts/register_customer.html', {'form': form})


def register_technician(request):
    if request.user.is_authenticated:
        return redirect('login_redirect')

    if request.method == 'POST':
        form = TechnicianRegistrationForm(request.POST, request.FILES)
        if form.is_valid():
            user = form.save()
            send_notification(
                user=user,
                title="Technician Application Received",
                message="Thank you for registering. Your profile is currently under review by our admin team.",
                link="/technician/dashboard/",
                notification_type="VERIFICATION"
            )
            login(request, user)
            messages.success(request, "Registration submitted! Your profile is pending verification.")
            return redirect('technician_dashboard')
    else:
        form = TechnicianRegistrationForm()

    return render(request, 'accounts/register_technician.html', {'form': form})


@login_required
def login_redirect(request):
    if request.user.is_admin_user:
        return redirect('admin_dashboard')
    elif request.user.is_technician:
        return redirect('technician_dashboard')
    else:
        return redirect('customer_dashboard')
