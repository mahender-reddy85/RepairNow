from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.utils.http import url_has_allowed_host_and_scheme
from django.db.models import Avg, Count
from django.utils import timezone
from accounts.decorators import admin_required
from accounts.models import User, CustomerProfile
from technicians.models import TechnicianProfile
from services.models import ServiceCategory
from repairs.models import RepairRequest, Job
from reviews.models import Review, Complaint
from notifications.models import send_notification

@login_required
@admin_required
def admin_dashboard(request):
    total_customers = CustomerProfile.objects.count()
    total_technicians = TechnicianProfile.objects.count()
    verified_technicians = TechnicianProfile.objects.filter(verification_status=TechnicianProfile.VERIFICATION_VERIFIED).count()
    pending_verifications = TechnicianProfile.objects.filter(verification_status=TechnicianProfile.VERIFICATION_PENDING).count()
    
    active_requests = RepairRequest.objects.exclude(status__in=[
        RepairRequest.STATUS_COMPLETED,
        RepairRequest.STATUS_CANCELLED,
        RepairRequest.STATUS_REJECTED
    ]).count()
    
    completed_jobs = Job.objects.filter(status=Job.STATUS_COMPLETED).count()
    cancelled_jobs = Job.objects.filter(status=Job.STATUS_CANCELLED).count()

    avg_rating_agg = Review.objects.aggregate(avg=Avg('rating'))
    avg_rating = round(avg_rating_agg['avg'] or 0.0, 1)

    recent_requests = RepairRequest.objects.all().order_by('-created_at')[:6]
    pending_techs = TechnicianProfile.objects.filter(verification_status=TechnicianProfile.VERIFICATION_PENDING)[:5]
    open_complaints = Complaint.objects.filter(status__in=['OPEN', 'IN_REVIEW'])[:5]

    context = {
        'total_customers': total_customers,
        'total_technicians': total_technicians,
        'verified_technicians': verified_technicians,
        'pending_verifications': pending_verifications,
        'active_requests': active_requests,
        'completed_jobs': completed_jobs,
        'cancelled_jobs': cancelled_jobs,
        'average_platform_rating': avg_rating,
        'recent_requests': recent_requests,
        'pending_techs': pending_techs,
        'open_complaints': open_complaints,
    }
    return render(request, 'admin/dashboard.html', context)


@login_required
@admin_required
def admin_users(request):
    q = request.GET.get('q', '').strip()
    role_filter = request.GET.get('role')
    
    users = User.objects.all().order_by('-date_joined')
    if q:
        users = users.filter(username__icontains=q) | users.filter(email__icontains=q)
    if role_filter:
        users = users.filter(role=role_filter)

    return render(request, 'admin/users.html', {'users': users, 'query': q, 'role_filter': role_filter})


@login_required
@admin_required
@require_POST
def admin_toggle_user_active(request, user_id):
    user = get_object_or_404(User, id=user_id)
    if user == request.user:
        messages.error(request, "You cannot deactivate your own admin account.")
        return redirect('admin_users')
    
    user.is_active = not user.is_active
    user.save(update_fields=['is_active'])
    status_text = "activated" if user.is_active else "deactivated"
    messages.success(request, f"User '{user.username}' has been {status_text}.")
    return redirect('admin_users')


@login_required
@admin_required
def admin_technicians(request):
    q = request.GET.get('q', '').strip()
    status_filter = request.GET.get('status')
    
    techs = TechnicianProfile.objects.all().order_by('-created_at')
    if q:
        techs = techs.filter(full_name__icontains=q) | techs.filter(user__username__icontains=q) | techs.filter(city__icontains=q)
    if status_filter:
        techs = techs.filter(verification_status=status_filter)

    return render(request, 'admin/technicians.html', {'technicians': techs, 'query': q, 'status_filter': status_filter})


@login_required
@admin_required
def admin_verifications(request):
    pending_techs = TechnicianProfile.objects.filter(verification_status=TechnicianProfile.VERIFICATION_PENDING).order_by('-created_at')
    return render(request, 'admin/verifications.html', {'technicians': pending_techs})


@login_required
@admin_required
@require_POST
def admin_verify_technician(request, tech_id, action):
    tech = get_object_or_404(TechnicianProfile, id=tech_id)
    if action == 'approve':
        tech.verification_status = TechnicianProfile.VERIFICATION_VERIFIED
        tech.save(update_fields=['verification_status'])
        send_notification(
            user=tech.user,
            title="Profile Verified!",
            message="Congratulations! Your technician profile has been verified. You can now receive repair requests.",
            link="/technician/dashboard/",
            notification_type="VERIFIED"
        )
        messages.success(request, f"Technician {tech.full_name} has been verified.")
    elif action == 'reject':
        tech.verification_status = TechnicianProfile.VERIFICATION_REJECTED
        tech.save(update_fields=['verification_status'])
        send_notification(
            user=tech.user,
            title="Verification Declined",
            message="Your technician verification was not approved. Please contact support or update your credentials.",
            link="/technician/profile/",
            notification_type="VERIFIED"
        )
        messages.info(request, f"Technician {tech.full_name} verification was rejected.")
    elif action == 'suspend':
        tech.verification_status = TechnicianProfile.VERIFICATION_SUSPENDED
        tech.save(update_fields=['verification_status'])
        messages.warning(request, f"Technician {tech.full_name} has been suspended.")
    else:
        messages.error(request, f"Invalid verification action '{action}'.")
        
    referer = request.META.get('HTTP_REFERER')
    if referer and url_has_allowed_host_and_scheme(url=referer, allowed_hosts={request.get_host()}):
        return redirect(referer)
    return redirect('admin_technicians')


@login_required
@admin_required
def admin_services(request):
    categories = ServiceCategory.objects.all().order_by('name')
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'create':
            name = request.POST.get('name', '').strip()
            desc = request.POST.get('description', '').strip()
            icon = request.POST.get('icon', 'fa-wrench').strip()
            if name:
                ServiceCategory.objects.create(name=name, description=desc, icon=icon)
                messages.success(request, f"Service category '{name}' created.")
        elif action == 'toggle':
            cat_id = request.POST.get('category_id')
            cat = get_object_or_404(ServiceCategory, id=cat_id)
            cat.is_active = not cat.is_active
            cat.save(update_fields=['is_active'])
            messages.success(request, f"Service category '{cat.name}' toggled.")
        return redirect('admin_services')

    return render(request, 'admin/services.html', {'categories': categories})


@login_required
@admin_required
def admin_requests(request):
    status_filter = request.GET.get('status')
    service_filter = request.GET.get('service')
    urgency_filter = request.GET.get('urgency')
    q = request.GET.get('q', '').strip()

    requests_qs = RepairRequest.objects.all().order_by('-created_at')
    if status_filter:
        requests_qs = requests_qs.filter(status=status_filter)
    if service_filter:
        requests_qs = requests_qs.filter(service_category_id=service_filter)
    if urgency_filter:
        requests_qs = requests_qs.filter(urgency=urgency_filter)
    if q:
        requests_qs = requests_qs.filter(device_name__icontains=q) | requests_qs.filter(customer__full_name__icontains=q)

    categories = ServiceCategory.objects.filter(is_active=True)
    return render(request, 'admin/requests.html', {
        'requests': requests_qs,
        'categories': categories,
        'status_filter': status_filter,
        'service_filter': service_filter,
        'urgency_filter': urgency_filter,
        'query': q,
    })


@login_required
@admin_required
def admin_reviews(request):
    reviews = Review.objects.all().order_by('-created_at')
    if request.method == 'POST' and request.POST.get('action') == 'delete':
        rev_id = request.POST.get('review_id')
        review = get_object_or_404(Review, id=rev_id)
        tech = review.technician
        review.delete()
        tech.update_rating_stats()
        messages.success(request, "Review deleted.")
        return redirect('admin_reviews')

    return render(request, 'admin/reviews.html', {'reviews': reviews})


@login_required
@admin_required
def admin_complaints(request):
    complaints = Complaint.objects.all().order_by('-created_at')
    if request.method == 'POST':
        comp_id = request.POST.get('complaint_id')
        new_status = request.POST.get('status')
        admin_response = request.POST.get('admin_response', '')
        complaint = get_object_or_404(Complaint, id=comp_id)
        complaint.status = new_status
        complaint.admin_response = admin_response
        complaint.save()

        send_notification(
            user=complaint.user,
            title="Complaint Status Updated",
            message=f"Your complaint regarding '{complaint.subject}' has been updated to {complaint.get_status_display()}.",
            link="",
            notification_type="COMPLAINT"
        )
        messages.success(request, f"Complaint #{complaint.id} updated.")
        return redirect('admin_complaints')

    return render(request, 'admin/complaints.html', {'complaints': complaints})
