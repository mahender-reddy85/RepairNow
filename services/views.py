from django.shortcuts import render, get_object_or_404
from .models import ServiceCategory
from technicians.models import TechnicianProfile
from repairs.models import Job

def home(request):
    categories = ServiceCategory.objects.filter(is_active=True)[:8]
    verified_tech_count = TechnicianProfile.objects.filter(
        verification_status=TechnicianProfile.VERIFICATION_VERIFIED,
        user__is_active=True
    ).count()
    completed_jobs_count = Job.objects.filter(status=Job.STATUS_COMPLETED).count()
    
    context = {
        'categories': categories,
        'verified_tech_count': max(verified_tech_count, 12),
        'completed_jobs_count': max(completed_jobs_count, 45),
        'satisfaction_rate': 98,
    }
    return render(request, 'home.html', context)


def about(request):
    return render(request, 'about.html')


def services_list(request):
    query = request.GET.get('q', '').strip()
    categories = ServiceCategory.objects.filter(is_active=True)
    if query:
        categories = categories.filter(name__icontains=query) | categories.filter(description__icontains=query)

    return render(request, 'services.html', {
        'categories': categories,
        'query': query,
    })


def service_detail(request, slug):
    category = get_object_or_404(ServiceCategory, slug=slug, is_active=True)
    technicians = TechnicianProfile.objects.filter(
        skills__service_category=category,
        verification_status=TechnicianProfile.VERIFICATION_VERIFIED,
        user__is_active=True
    ).distinct()

    return render(request, 'service_detail.html', {
        'category': category,
        'technicians': technicians,
    })
