from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.utils import timezone
from accounts.decorators import technician_required
from accounts.forms import TechnicianProfileUpdateForm
from .models import TechnicianProfile, Availability, TechnicianSkill
from services.models import ServiceCategory
from repairs.models import RepairRequest, Job, JobStatusHistory
from reviews.models import Review
from notifications.models import send_notification

@login_required
@technician_required
def technician_dashboard(request):
    profile = request.user.technician_profile
    new_requests = RepairRequest.objects.filter(
        selected_technician=profile,
        status=RepairRequest.STATUS_TECHNICIAN_SELECTED
    ).order_by('-created_at')
    
    active_jobs = Job.objects.filter(
        technician=profile,
        status__in=[Job.STATUS_ACCEPTED, Job.STATUS_ON_THE_WAY, Job.STATUS_ARRIVED, Job.STATUS_IN_PROGRESS]
    ).order_by('-created_at')

    completed_jobs_count = Job.objects.filter(technician=profile, status=Job.STATUS_COMPLETED).count()

    context = {
        'profile': profile,
        'new_requests_count': new_requests.count(),
        'active_jobs_count': active_jobs.count(),
        'completed_jobs_count': completed_jobs_count,
        'average_rating': profile.average_rating,
        'new_requests': new_requests[:5],
        'active_jobs': active_jobs[:5],
        'view_mode': 'list',
    }
    return render(request, 'technician/dashboard.html', context)


@login_required
@technician_required
def technician_profile(request):
    profile = request.user.technician_profile
    if request.method == 'POST':
        form = TechnicianProfileUpdateForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            selected_skills = form.cleaned_data.get('skills')
            if selected_skills is not None:
                TechnicianSkill.objects.filter(technician=profile).delete()
                for cat in selected_skills:
                    TechnicianSkill.objects.create(technician=profile, service_category=cat)

            messages.success(request, "Your profile has been updated successfully.")
            return redirect('technician_profile')
    else:
        initial_skills = [ts.service_category for ts in profile.skills.all()]
        form = TechnicianProfileUpdateForm(instance=profile, initial={'skills': initial_skills})

    return render(request, 'technician/profile.html', {'form': form, 'profile': profile})


@login_required
@technician_required
def technician_availability(request):
    profile = request.user.technician_profile
    days = Availability.DAY_CHOICES

    existing_slots = {slot.day_of_week: slot for slot in profile.availability_schedule.all()}
    schedule = []
    for day_num, day_name in days:
        slot = existing_slots.get(day_num)
        if not slot:
            slot = Availability.objects.create(technician=profile, day_of_week=day_num, is_available=True)
        schedule.append((day_name, slot))

    if request.method == 'POST':
        status = request.POST.get('availability_status')
        if status in [TechnicianProfile.AVAILABILITY_AVAILABLE, TechnicianProfile.AVAILABILITY_BUSY, TechnicianProfile.AVAILABILITY_OFFLINE]:
            profile.availability_status = status
            profile.save(update_fields=['availability_status'])
            messages.success(request, f"Availability status set to {profile.get_availability_status_display()}.")

        for day_num, _ in days:
            slot = existing_slots.get(day_num)
            is_avail = request.POST.get(f'avail_{day_num}') == 'on'
            s_time = request.POST.get(f'start_{day_num}', '09:00')
            e_time = request.POST.get(f'end_{day_num}', '18:00')
            if slot:
                slot.is_available = is_avail
                slot.start_time = s_time
                slot.end_time = e_time
                slot.save()
        messages.success(request, "Weekly schedule updated successfully.")
        return redirect('technician_dashboard')

    return render(request, 'technician/dashboard.html', {
        'profile': profile,
        'schedule': schedule,
        'view_mode': 'availability',
    })


@login_required
@technician_required
def toggle_availability_ajax(request):
    if request.method == 'POST':
        new_status = request.POST.get('status')
        profile = request.user.technician_profile
        if new_status in [TechnicianProfile.AVAILABILITY_AVAILABLE, TechnicianProfile.AVAILABILITY_BUSY, TechnicianProfile.AVAILABILITY_OFFLINE]:
            profile.availability_status = new_status
            profile.save(update_fields=['availability_status'])
            return JsonResponse({'success': True, 'status': new_status, 'status_display': profile.get_availability_status_display()})
    return JsonResponse({'success': False, 'error': 'Invalid status'}, status=400)


@login_required
@technician_required
def technician_requests(request):
    profile = request.user.technician_profile
    requests_qs = RepairRequest.objects.filter(selected_technician=profile)

    status_filter = request.GET.get('status')
    urgency_filter = request.GET.get('urgency')
    service_filter = request.GET.get('service')

    if status_filter:
        requests_qs = requests_qs.filter(status=status_filter)
    if urgency_filter:
        requests_qs = requests_qs.filter(urgency=urgency_filter)
    if service_filter:
        requests_qs = requests_qs.filter(service_category_id=service_filter)

    categories = ServiceCategory.objects.filter(is_active=True)
    return render(request, 'technician/requests.html', {
        'requests': requests_qs,
        'categories': categories,
        'selected_status': status_filter,
        'selected_urgency': urgency_filter,
        'selected_service': service_filter,
        'view_mode': 'list',
    })


@login_required
@technician_required
def technician_request_detail(request, request_id):
    profile = request.user.technician_profile
    repair_request = get_object_or_404(RepairRequest, id=request_id, selected_technician=profile)
    
    job = getattr(repair_request, 'job', None)

    return render(request, 'technician/requests.html', {
        'repair_request': repair_request,
        'job': job,
        'view_mode': 'detail',
    })


@login_required
@technician_required
def technician_accept_request(request, request_id):
    profile = request.user.technician_profile
    repair_request = get_object_or_404(RepairRequest, id=request_id, selected_technician=profile)

    if repair_request.status != RepairRequest.STATUS_TECHNICIAN_SELECTED:
        messages.warning(request, "This request is no longer available to accept.")
        return redirect('technician_requests')

    repair_request.status = RepairRequest.STATUS_ACCEPTED
    repair_request.save(update_fields=['status', 'updated_at'])

    job, created = Job.objects.get_or_create(
        repair_request=repair_request,
        defaults={
            'technician': profile,
            'customer': repair_request.customer,
            'status': Job.STATUS_ACCEPTED,
        }
    )

    JobStatusHistory.objects.create(
        job=job,
        status=Job.STATUS_ACCEPTED,
        changed_by=request.user,
        note=f"Technician {profile.full_name} accepted the repair request."
    )

    send_notification(
        user=repair_request.customer.user,
        title="Repair Request Accepted!",
        message=f"{profile.full_name} has accepted your repair request for {repair_request.device_name}.",
        link=f"/customer/repair/{repair_request.id}/track/",
        notification_type="STATUS_UPDATE"
    )

    messages.success(request, f"You have accepted request #{repair_request.id}. Job created!")
    return redirect('technician_job_detail', job_id=job.id)


@login_required
@technician_required
def technician_reject_request(request, request_id):
    profile = request.user.technician_profile
    repair_request = get_object_or_404(RepairRequest, id=request_id, selected_technician=profile)

    if repair_request.status != RepairRequest.STATUS_TECHNICIAN_SELECTED:
        messages.warning(request, "This request cannot be rejected at this stage.")
        return redirect('technician_requests')

    repair_request.status = RepairRequest.STATUS_REJECTED
    repair_request.selected_technician = None
    repair_request.save(update_fields=['status', 'selected_technician', 'updated_at'])

    send_notification(
        user=repair_request.customer.user,
        title="Technician Unavailable",
        message=f"{profile.full_name} was unable to accept your request. Please select another technician.",
        link=f"/customer/repair/{repair_request.id}/matches/",
        notification_type="STATUS_UPDATE"
    )

    messages.info(request, f"You rejected request #{repair_request.id}.")
    return redirect('technician_requests')


@login_required
@technician_required
def technician_jobs(request):
    profile = request.user.technician_profile
    jobs = Job.objects.filter(technician=profile).order_by('-created_at')
    status_filter = request.GET.get('status')
    if status_filter:
        jobs = jobs.filter(status=status_filter)

    return render(request, 'technician/jobs.html', {'jobs': jobs, 'selected_status': status_filter, 'view_mode': 'list'})


@login_required
@technician_required
def technician_job_detail(request, job_id):
    profile = request.user.technician_profile
    job = get_object_or_404(Job, id=job_id, technician=profile)
    history = job.status_history.all().order_by('timestamp')
    
    return render(request, 'technician/jobs.html', {
        'job': job,
        'history': history,
        'view_mode': 'detail',
    })


@login_required
@technician_required
def technician_update_job_status(request, job_id):
    profile = request.user.technician_profile
    job = get_object_or_404(Job, id=job_id, technician=profile)

    if request.method == 'POST':
        new_status = request.POST.get('status')
        note = request.POST.get('notes', '').strip()
        final_cost = request.POST.get('final_cost')

        if new_status == Job.STATUS_COMPLETED:
            if not final_cost:
                messages.error(request, "Final billable cost is required to complete the job.")
                return redirect('technician_job_detail', job_id=job.id)
            try:
                job.final_cost = float(final_cost)
            except ValueError:
                messages.error(request, "Invalid final cost amount.")
                return redirect('technician_job_detail', job_id=job.id)

        try:
            job.notes = note
            job.transition_to(new_status, user=request.user, note=note)

            status_labels = {
                Job.STATUS_ON_THE_WAY: ("Technician On The Way", f"{profile.full_name} is heading to your location."),
                Job.STATUS_ARRIVED: ("Technician Arrived", f"{profile.full_name} has arrived at your address."),
                Job.STATUS_IN_PROGRESS: ("Repair In Progress", f"{profile.full_name} has started inspecting/repairing."),
                Job.STATUS_COMPLETED: ("Repair Completed!", f"Your repair is complete. Final bill: ₹{job.final_cost}. Please leave a rating!"),
            }
            if new_status in status_labels:
                title, msg = status_labels[new_status]
                send_notification(
                    user=job.customer.user,
                    title=title,
                    message=msg,
                    link=f"/customer/repair/{job.repair_request.id}/track/",
                    notification_type="STATUS_UPDATE"
                )

            messages.success(request, f"Job status updated to {job.get_status_display()}.")
        except Exception as e:
            messages.error(request, f"Status update failed: {str(e)}")

    return redirect('technician_job_detail', job_id=job.id)


@login_required
@technician_required
def technician_history(request):
    profile = request.user.technician_profile
    completed_jobs = Job.objects.filter(technician=profile, status=Job.STATUS_COMPLETED).order_by('-completed_date')
    return render(request, 'technician/history.html', {'completed_jobs': completed_jobs})


@login_required
@technician_required
def technician_reviews(request):
    profile = request.user.technician_profile
    reviews = Review.objects.filter(technician=profile).order_by('-created_at')
    return render(request, 'technician/reviews.html', {
        'profile': profile,
        'reviews': reviews,
    })


@login_required
@technician_required
def technician_notifications(request):
    notifications = request.user.notifications.all().order_by('-created_at')
    return render(request, 'technician/notifications.html', {'notifications': notifications})
