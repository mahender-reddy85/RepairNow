from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponseForbidden
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.db import transaction
from accounts.decorators import customer_required
from accounts.forms import CustomerProfileUpdateForm
from .models import RepairRequest, TechnicianMatch, Job, JobStatusHistory
from .forms import RepairRequestForm
from .matching import find_and_rank_technicians
from technicians.models import TechnicianProfile
from notifications.models import send_notification

@login_required
@customer_required
def customer_dashboard(request):
    profile = request.user.customer_profile
    active_requests = RepairRequest.objects.filter(
        customer=profile,
        status__in=[
            RepairRequest.STATUS_PENDING,
            RepairRequest.STATUS_MATCHING,
            RepairRequest.STATUS_TECHNICIAN_SELECTED,
            RepairRequest.STATUS_ACCEPTED,
            RepairRequest.STATUS_ON_THE_WAY,
            RepairRequest.STATUS_ARRIVED,
            RepairRequest.STATUS_IN_PROGRESS,
            RepairRequest.STATUS_REJECTED,
        ]
    ).order_by('-created_at')

    completed_jobs = Job.objects.filter(customer=profile, status=Job.STATUS_COMPLETED).order_by('-completed_date')
    pending_count = active_requests.filter(status__in=[
        RepairRequest.STATUS_PENDING,
        RepairRequest.STATUS_MATCHING,
        RepairRequest.STATUS_TECHNICIAN_SELECTED,
        RepairRequest.STATUS_REJECTED,
    ]).count()
    ongoing_count = active_requests.filter(status__in=[
        RepairRequest.STATUS_ACCEPTED,
        RepairRequest.STATUS_ON_THE_WAY,
        RepairRequest.STATUS_ARRIVED,
        RepairRequest.STATUS_IN_PROGRESS,
    ]).count()

    return render(request, 'customer/dashboard.html', {
        'profile': profile,
        'active_requests': active_requests[:5],
        'pending_count': pending_count,
        'ongoing_count': ongoing_count,
        'completed_count': completed_jobs.count(),
        'recent_history': completed_jobs[:5],
    })


@login_required
@customer_required
def customer_profile(request):
    profile = request.user.customer_profile
    if request.method == 'POST':
        form = CustomerProfileUpdateForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, "Profile updated successfully.")
            return redirect('customer_profile')
    else:
        form = CustomerProfileUpdateForm(instance=profile)

    return render(request, 'customer/profile.html', {'form': form, 'profile': profile})


@login_required
@customer_required
def customer_repair_create(request):
    profile = request.user.customer_profile
    if request.method == 'POST':
        form = RepairRequestForm(request.POST, request.FILES)
        if form.is_valid():
            repair_request = form.save(commit=False)
            repair_request.customer = profile
            if profile.latitude and profile.longitude:
                repair_request.latitude = profile.latitude
                repair_request.longitude = profile.longitude
            repair_request.status = RepairRequest.STATUS_PENDING
            repair_request.save()

            find_and_rank_technicians(repair_request)

            send_notification(
                user=request.user,
                title="Repair Request Created",
                message=f"Your request for {repair_request.device_name} has been submitted. Technicians have been matched!",
                link=f"/customer/repair/{repair_request.id}/matches/",
                notification_type="REQUEST_CREATED"
            )

            messages.success(request, "Repair request created! Review your matched technicians below.")
            return redirect('customer_repair_matches', request_id=repair_request.id)
    else:
        initial = {
            'location': profile.address,
            'city': profile.city,
            'preferred_date': timezone.now().date(),
        }
        form = RepairRequestForm(initial=initial)

    return render(request, 'customer/repair.html', {'form': form, 'view_mode': 'create'})


@login_required
@customer_required
def customer_repair_list(request):
    profile = request.user.customer_profile
    requests_qs = RepairRequest.objects.filter(customer=profile).order_by('-created_at')
    return render(request, 'customer/repair.html', {'requests': requests_qs, 'view_mode': 'list'})


@login_required
@customer_required
def customer_repair_detail(request, request_id):
    profile = request.user.customer_profile
    repair_request = get_object_or_404(RepairRequest, id=request_id)

    if repair_request.customer != profile and not request.user.is_admin_user:
        return HttpResponseForbidden("You do not have permission to view this request.")

    job = getattr(repair_request, 'job', None)
    return render(request, 'customer/repair.html', {
        'repair_request': repair_request,
        'job': job,
        'view_mode': 'detail',
    })


@login_required
@customer_required
def customer_repair_matches(request, request_id):
    profile = request.user.customer_profile
    repair_request = get_object_or_404(RepairRequest, id=request_id)

    if repair_request.customer != profile and not request.user.is_admin_user:
        return HttpResponseForbidden("You do not have permission to view these matches.")

    matches = repair_request.matches.select_related('technician').all().order_by('-match_score', 'distance')
    if not matches.exists():
        find_and_rank_technicians(repair_request)
        matches = repair_request.matches.select_related('technician').all().order_by('-match_score', 'distance')

    min_rating = request.GET.get('rating')
    max_cost = request.GET.get('max_cost')
    avail_only = request.GET.get('available_only')

    filtered_matches = []
    for m in matches:
        if min_rating and m.technician.average_rating < float(min_rating):
            continue
        if max_cost and m.technician.estimated_cost_max > float(max_cost):
            continue
        if avail_only and m.technician.availability_status != TechnicianProfile.AVAILABILITY_AVAILABLE:
            continue
        filtered_matches.append(m)

    return render(request, 'customer/matches.html', {
        'repair_request': repair_request,
        'matches': filtered_matches,
        'total_count': len(filtered_matches),
    })


@login_required
@customer_required
@require_POST
def customer_select_technician(request, request_id, tech_id):
    profile = request.user.customer_profile

    with transaction.atomic():
        repair_request = get_object_or_404(
            RepairRequest.objects.select_for_update(),
            id=request_id
        )

        if repair_request.customer != profile:
            return HttpResponseForbidden("Unauthorized.")

        selectable_statuses = [
            RepairRequest.STATUS_PENDING,
            RepairRequest.STATUS_MATCHING,
            RepairRequest.STATUS_REJECTED,
        ]
        if repair_request.status not in selectable_statuses:
            messages.warning(request, "A technician has already been selected or this request is currently active.")
            return redirect('customer_repair_track', request_id=repair_request.id)

        technician = get_object_or_404(
            TechnicianProfile,
            id=tech_id,
            verification_status=TechnicianProfile.VERIFICATION_VERIFIED,
            user__is_active=True
        )

        if repair_request.rejections.filter(technician=technician).exists():
            messages.error(
                request,
                f"{technician.full_name} has declined this repair request. Please select an alternate technician."
            )
            return redirect('customer_repair_matches', request_id=repair_request.id)

        if not repair_request.matches.filter(technician=technician).exists():
            messages.error(
                request,
                "The selected technician is not an eligible match for this repair request."
            )
            return redirect('customer_repair_matches', request_id=repair_request.id)

        repair_request.selected_technician = technician
        repair_request.status = RepairRequest.STATUS_TECHNICIAN_SELECTED
        repair_request.save(update_fields=['selected_technician', 'status', 'updated_at'])

        send_notification(
            user=technician.user,
            title="New Repair Request Assigned!",
            message=f"{profile.full_name} has requested your service for {repair_request.device_name}.",
            link=f"/technician/requests/{repair_request.id}/",
            notification_type="JOB_REQUEST"
        )

        send_notification(
            user=request.user,
            title="Technician Selected",
            message=f"You selected {technician.full_name}. We have sent your request to the technician.",
            link=f"/customer/repair/{repair_request.id}/track/",
            notification_type="TECHNICIAN_SELECTED"
        )

    messages.success(request, f"You have selected {technician.full_name}. Awaiting technician acceptance.")
    return redirect('customer_repair_track', request_id=repair_request.id)


@login_required
@customer_required
def customer_repair_track(request, request_id):
    profile = request.user.customer_profile
    repair_request = get_object_or_404(RepairRequest, id=request_id)

    if repair_request.customer != profile and not request.user.is_admin_user:
        return HttpResponseForbidden("Unauthorized.")

    job = getattr(repair_request, 'job', None)
    history = job.status_history.all().order_by('timestamp') if job else []
    review = getattr(job, 'review', None) if job else None

    return render(request, 'customer/track.html', {
        'repair_request': repair_request,
        'job': job,
        'history': history,
        'review': review,
    })


@login_required
@customer_required
def customer_repair_status_api(request, request_id):
    profile = request.user.customer_profile
    repair_request = get_object_or_404(RepairRequest, id=request_id)
    if repair_request.customer != profile and not request.user.is_admin_user:
        return JsonResponse({'error': 'Unauthorized'}, status=403)

    job = getattr(repair_request, 'job', None)
    return JsonResponse({
        'request_status': repair_request.status,
        'request_status_display': repair_request.get_status_display(),
        'job_status': job.status if job else None,
        'job_status_display': job.get_status_display() if job else None,
        'is_completed': repair_request.status == RepairRequest.STATUS_COMPLETED,
    })


@login_required
@customer_required
@require_POST
def customer_repair_cancel(request, request_id):
    profile = request.user.customer_profile

    with transaction.atomic():
        repair_request = get_object_or_404(
            RepairRequest.objects.select_for_update(),
            id=request_id
        )

        if repair_request.customer != profile:
            return HttpResponseForbidden("Unauthorized.")

        if not repair_request.can_be_cancelled():
            messages.error(request, "This repair request cannot be cancelled because it is already in progress or completed.")
            return redirect('customer_repair_track', request_id=repair_request.id)

        repair_request.status = RepairRequest.STATUS_CANCELLED
        repair_request.save(update_fields=['status', 'updated_at'])

        if hasattr(repair_request, 'job'):
            repair_request.job.status = Job.STATUS_CANCELLED
            repair_request.job.save(update_fields=['status', 'updated_at'])

        if repair_request.selected_technician:
            send_notification(
                user=repair_request.selected_technician.user,
                title="Request Cancelled",
                message=f"Customer {profile.full_name} cancelled the repair request for {repair_request.device_name}.",
                link="/technician/requests/",
                notification_type="JOB_CANCELLED"
            )

    messages.info(request, "Repair request has been cancelled.")
    return redirect('customer_dashboard')


@login_required
@customer_required
def customer_history(request):
    profile = request.user.customer_profile
    jobs = Job.objects.filter(customer=profile).order_by('-created_at')
    return render(request, 'customer/history.html', {'jobs': jobs})


@login_required
@customer_required
def customer_notifications(request):
    notifications = request.user.notifications.all().order_by('-created_at')
    return render(request, 'customer/notifications.html', {'notifications': notifications})
