import math
from django.utils import timezone
from .models import TechnicianMatch, RepairRequest
from technicians.models import TechnicianProfile

EARTH_RADIUS_KM = 6371.0

def haversine_distance(lat1, lon1, lat2, lon2):
    if None in (lat1, lon1, lat2, lon2):
        return None

    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = (math.sin(delta_phi / 2.0) ** 2 + \
         math.cos(phi1) * math.cos(phi2) * \
         math.sin(delta_lambda / 2.0) ** 2)
    c = 2.0 * math.asin(math.sqrt(max(0.0, min(1.0, a))))
    return round(EARTH_RADIUS_KM * c, 2)


def calculate_distance_score(distance_km):
    if distance_km is None:
        return 70.0
    if distance_km <= 2.0:
        return 100.0
    elif distance_km <= 5.0:
        return 90.0
    elif distance_km <= 10.0:
        return 75.0
    elif distance_km <= 20.0:
        return 50.0
    elif distance_km <= 30.0:
        return 30.0
    else:
        return 10.0


def calculate_availability_score(technician, preferred_date, urgency):
    weekday = preferred_date.weekday()
    schedule_slot = technician.availability_schedule.filter(day_of_week=weekday).first()

    score = 70.0
    if schedule_slot:
        score = 100.0 if schedule_slot.is_available else 20.0
    else:
        if technician.availability_status == TechnicianProfile.AVAILABILITY_AVAILABLE:
            score = 90.0
        elif technician.availability_status == TechnicianProfile.AVAILABILITY_BUSY:
            score = 45.0
        else:
            score = 10.0

    if urgency == RepairRequest.URGENCY_EMERGENCY:
        if technician.availability_status == TechnicianProfile.AVAILABILITY_AVAILABLE:
            score = min(100.0, score + 10.0)
        else:
            score = max(5.0, score - 40.0)
    elif urgency == RepairRequest.URGENCY_HIGH:
        if technician.availability_status != TechnicianProfile.AVAILABILITY_AVAILABLE:
            score = max(15.0, score - 20.0)

    return score


def calculate_cost_score(technician, budget):
    if not budget:
        return 90.0

    budget = float(budget)
    min_cost = float(technician.estimated_cost_min)
    max_cost = float(technician.estimated_cost_max)

    if min_cost <= budget <= max_cost:
        return 100.0
    elif budget > max_cost:
        return 95.0
    else:
        gap = min_cost - budget
        penalty = (gap / min_cost) * 100.0
        return max(15.0, round(100.0 - penalty, 1))


def find_and_rank_technicians(repair_request):
    candidate_technicians = TechnicianProfile.objects.filter(
        user__is_active=True,
        verification_status=TechnicianProfile.VERIFICATION_VERIFIED,
        skills__service_category=repair_request.service_category
    ).distinct()

    matches = []
    urgency = repair_request.urgency
    req_lat = repair_request.latitude
    req_lon = repair_request.longitude
    req_city = (repair_request.city or '').strip().lower()

    for tech in candidate_technicians:
        tech_city = (tech.city or '').strip().lower()
        distance = None
        if req_lat and req_lon and tech.latitude and tech.longitude:
            distance = haversine_distance(req_lat, req_lon, tech.latitude, tech.longitude)
        else:
            if req_city and tech_city and req_city == tech_city:
                if tech.service_area and any(w in tech.service_area.lower() for w in repair_request.location.lower().split()):
                    distance = 2.5
                else:
                    distance = 5.0
            else:
                distance = 28.0

        if urgency == RepairRequest.URGENCY_EMERGENCY and (distance > 35.0 or tech.availability_status == TechnicianProfile.AVAILABILITY_OFFLINE):
            continue

        exp_bonus = min(5.0, tech.experience * 1.0)
        skill_score = min(100.0, 95.0 + exp_bonus)

        avail_score = calculate_availability_score(tech, repair_request.preferred_date, urgency)

        dist_score = calculate_distance_score(distance)

        if tech.total_reviews_count > 0:
            rating_score = round((tech.average_rating / 5.0) * 100.0, 1)
        else:
            rating_score = 75.0

        cost_score = calculate_cost_score(tech, repair_request.budget)

        if urgency == RepairRequest.URGENCY_EMERGENCY:
            total_match_score = (
                (skill_score * 0.25) +
                (avail_score * 0.30) +
                (dist_score * 0.25) +
                (rating_score * 0.12) +
                (cost_score * 0.08)
            )
        else:
            total_match_score = (
                (skill_score * 0.35) +
                (avail_score * 0.20) +
                (dist_score * 0.20) +
                (rating_score * 0.15) +
                (cost_score * 0.10)
            )

        total_match_score = round(min(100.0, max(10.0, total_match_score)), 1)

        matches.append({
            'technician': tech,
            'match_score': total_match_score,
            'skill_score': round(skill_score, 1),
            'availability_score': round(avail_score, 1),
            'distance_score': round(dist_score, 1),
            'rating_score': round(rating_score, 1),
            'cost_score': round(cost_score, 1),
            'distance': distance or 0.0,
        })

    matches.sort(key=lambda x: (-x['match_score'], x['distance']))

    TechnicianMatch.objects.filter(repair_request=repair_request).delete()
    persisted_matches = []
    for m in matches:
        match_obj = TechnicianMatch.objects.create(
            repair_request=repair_request,
            technician=m['technician'],
            match_score=m['match_score'],
            skill_score=m['skill_score'],
            availability_score=m['availability_score'],
            distance_score=m['distance_score'],
            rating_score=m['rating_score'],
            cost_score=m['cost_score'],
            distance=m['distance']
        )
        persisted_matches.append(match_obj)

    if persisted_matches and repair_request.status == RepairRequest.STATUS_PENDING:
        repair_request.status = RepairRequest.STATUS_MATCHING
        repair_request.save(update_fields=['status', 'updated_at'])

    return persisted_matches
