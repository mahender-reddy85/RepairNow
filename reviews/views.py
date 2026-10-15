from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from accounts.decorators import customer_required
from .models import Review, Complaint
from .forms import ReviewForm, ComplaintForm
from repairs.models import Job
from notifications.models import send_notification

@login_required
@customer_required
def submit_review(request, job_id):
    profile = request.user.customer_profile
    job = get_object_or_404(Job, id=job_id)

    if job.customer != profile:
        return HttpResponseForbidden("You are not authorized to review this job.")

    if job.status != Job.STATUS_COMPLETED:
        messages.error(request, "Reviews can only be submitted for completed repairs.")
        return redirect('customer_repair_track', request_id=job.repair_request.id)

    if hasattr(job, 'review'):
        messages.info(request, "You have already submitted a review for this repair.")
        return redirect('customer_repair_track', request_id=job.repair_request.id)

    if request.method == 'POST':
        form = ReviewForm(request.POST)
        if form.is_valid():
            review = form.save(commit=False)
            review.job = job
            review.customer = profile
            review.technician = job.technician
            review.save()

            send_notification(
                user=job.technician.user,
                title="New Review Received!",
                message=f"{profile.full_name} gave you a {review.rating}-star review for {job.repair_request.device_name}.",
                link="/technician/reviews/",
                notification_type="REVIEW_RECEIVED"
            )

            messages.success(request, "Thank you! Your review and rating have been posted.")
            return redirect('customer_repair_track', request_id=job.repair_request.id)
    else:
        form = ReviewForm()

    return render(request, 'customer/review.html', {
        'form': form,
        'job': job,
    })


@login_required
def submit_complaint(request, job_id=None):
    job = None
    if job_id:
        job = get_object_or_404(Job, id=job_id)
        if not (request.user == job.customer.user or request.user == job.technician.user or request.user.is_admin_user):
            return HttpResponseForbidden("You are not authorized to file a complaint for this repair job.")

    if request.method == 'POST':
        form = ComplaintForm(request.POST)
        if form.is_valid():
            complaint = form.save(commit=False)
            complaint.user = request.user
            complaint.job = job
            complaint.save()

            messages.success(request, "Your complaint has been submitted. Our admin team will investigate promptly.")
            if request.user.is_customer:
                return redirect('customer_dashboard')
            return redirect('technician_dashboard')
    else:
        form = ComplaintForm()

    return render(request, 'customer/repair.html', {
        'form': form,
        'job': job,
        'view_mode': 'complaint',
    })
