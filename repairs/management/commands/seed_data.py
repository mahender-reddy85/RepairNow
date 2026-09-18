from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
from accounts.models import CustomerProfile
from services.models import ServiceCategory
from technicians.models import TechnicianProfile, TechnicianSkill, Availability
from repairs.models import RepairRequest, Job, JobStatusHistory, TechnicianMatch
from repairs.matching import find_and_rank_technicians
from reviews.models import Review, Complaint
from notifications.models import Notification

User = get_user_model()


class Command(BaseCommand):
    help = "Seed database with realistic initial demonstration data for RepairNow."

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE("Seeding RepairNow database..."))

        admin_user, created = User.objects.get_or_create(
            username='repairnow',
            defaults={
                'email': 'admin@repairnow.com',
                'role': User.ROLE_ADMIN,
                'is_staff': True,
                'is_superuser': True,
                'phone': '9848022338',
            }
        )
        admin_user.set_password('123456')
        admin_user.save()
        self.stdout.write(self.style.SUCCESS("[OK] Admin user created: repairnow / 123456"))

        categories_data = [
            ('AC Repair', 'fa-snowflake', 'Split and window AC servicing, gas refilling, compressor troubleshooting, and PCB repair.'),
            ('Washing Machine Repair', 'fa-soap', 'Top-load, front-load and semi-automatic drum repairs, drain motor replacement, and vibration fixes.'),
            ('Refrigerator Repair', 'fa-temperature-arrow-down', 'Single and double door cooling issues, thermostat calibration, and gas leak sealing.'),
            ('Electrical Repair', 'fa-bolt', 'Short circuit diagnostics, switchboard installation, MCB tripping fixes, and house rewiring.'),
            ('Mobile Repair', 'fa-mobile-screen-button', 'Screen glass replacement, battery swaps, charging port soldering, and water damage recovery.'),
            ('Computer Repair', 'fa-laptop', 'Laptop hardware fixes, SSD upgrades, OS recovery, motherboard component repair, and thermal repasting.'),
            ('TV Repair', 'fa-tv', 'LED/LCD backlight panel replacements, motherboards, HDMI port replacements, and audio board fixes.'),
            ('Vehicle Repair', 'fa-motorcycle', 'Doorstep two-wheeler and four-wheeler breakdown assistance, brake servicing, and battery jumpstarts.'),
            ('Plumbing', 'fa-faucet-drip', 'Pipe leakage sealing, tap and valve replacements, sanitary fitting repairs, and blockage removal.'),
        ]

        category_objs = {}
        for name, icon, desc in categories_data:
            cat, _ = ServiceCategory.objects.get_or_create(
                name=name,
                defaults={'icon': icon, 'description': desc, 'is_active': True}
            )
            category_objs[name] = cat
        self.stdout.write(self.style.SUCCESS(f"[OK] {len(category_objs)} Service Categories initialized."))

        customers_data = [
            ('ramesh_v', 'ramesh@example.com', 'Ramesh Varma', '9876543210', 'Door 40-1-52, MG Road, Benz Circle', 'Vijayawada', 16.5033, 80.6465),
            ('priya_s', 'priya@example.com', 'Priya Sharma', '9876543211', 'Flat 302, Sri Krishna Apts, Bhavanipuram', 'Vijayawada', 16.5180, 80.6120),
            ('ananya_p', 'ananya@example.com', 'Ananya Patel', '9876543212', 'House 12-4, Ring Road, Gunadala', 'Vijayawada', 16.5250, 80.6650),
            ('vikram_r', 'vikram@example.com', 'Vikram Roy', '9876543213', 'Plot 88, Kaleswara Rao Market, Governorpet', 'Vijayawada', 16.5110, 80.6270),
        ]

        customer_profiles = []
        for uname, email, full_name, phone, address, city, lat, lon in customers_data:
            u, created = User.objects.get_or_create(
                username=uname,
                defaults={
                    'email': email,
                    'role': User.ROLE_CUSTOMER,
                    'phone': phone,
                }
            )
            u.set_password('user1234')
            u.save()
            cp, created = CustomerProfile.objects.get_or_create(
                user=u,
                defaults={
                    'full_name': full_name,
                    'phone': phone,
                    'address': address,
                    'city': city,
                    'latitude': lat,
                    'longitude': lon,
                    'state': 'Andhra Pradesh',
                    'postal_code': '520001',
                }
            )
            customer_profiles.append(cp)
        self.stdout.write(self.style.SUCCESS(f"[OK] {len(customer_profiles)} Customer accounts initialized. Password: user1234"))

        technicians_data = [
            (
                'suresh_tech', 'suresh.tech@example.com', 'Suresh Kumar', '9849112233',
                8, 'Benz Circle Area, MG Road', 'Workshop 1, MG Road',
                'Vijayawada', 16.5010, 80.6420, 500, 1000,
                TechnicianProfile.VERIFICATION_VERIFIED,
                TechnicianProfile.AVAILABILITY_AVAILABLE,
                ['AC Repair', 'Refrigerator Repair']
            ),
            (
                'naresh_ac', 'naresh.ac@example.com', 'Naresh Babu', '9849112244',
                5, 'Governorpet & Seetharampuram', 'Shop 12, Satyanarayanapuram',
                'Vijayawada', 16.5120, 80.6290, 400, 900,
                TechnicianProfile.VERIFICATION_VERIFIED,
                TechnicianProfile.AVAILABILITY_AVAILABLE,
                ['AC Repair', 'Electrical Repair']
            ),
            (
                'rajesh_washer', 'rajesh.w@example.com', 'Rajesh Mullapudi', '9849112255',
                6, 'Gunadala & Ramavarappadu', 'Plot 44, Gannavaram Road',
                'Vijayawada', 16.5280, 80.6700, 450, 1000,
                TechnicianProfile.VERIFICATION_VERIFIED,
                TechnicianProfile.AVAILABILITY_BUSY,
                ['Washing Machine Repair', 'Refrigerator Repair']
            ),
            (
                'manoj_mobile', 'manoj.mob@example.com', 'Manoj Paritala', '9849112266',
                4, 'City Center', 'Shop 4, Devi Complex, Eluru Road',
                'Vijayawada', 16.5100, 80.6300, 200, 700,
                TechnicianProfile.VERIFICATION_VERIFIED,
                TechnicianProfile.AVAILABILITY_AVAILABLE,
                ['Mobile Repair', 'Computer Repair', 'TV Repair']
            ),
            (
                'arun_plumber', 'arun.plumb@example.com', 'Arun Kumar P.', '9849112277',
                10, 'All of Vijayawada', 'Near Municipal Water Tank, Bhavanipuram',
                'Vijayawada', 16.5190, 80.6110, 300, 800,
                TechnicianProfile.VERIFICATION_VERIFIED,
                TechnicianProfile.AVAILABILITY_AVAILABLE,
                ['Plumbing', 'Electrical Repair']
            ),
            (
                'pending_tech', 'pending@example.com', 'Pending Verification', '9849112288',
                1, 'Bhavanipuram', 'Home Office',
                'Vijayawada', 16.5160, 80.6140, 350, 700,
                TechnicianProfile.VERIFICATION_PENDING,
                TechnicianProfile.AVAILABILITY_OFFLINE,
                ['AC Repair']
            ),
        ]

        technician_profiles = []
        days = list(range(7))
        for uname, email, full_name, phone, exp, sarea, address, city, lat, lon, cmin, cmax, vstatus, astatus, skills in technicians_data:
            u, created = User.objects.get_or_create(
                username=uname,
                defaults={
                    'email': email,
                    'role': User.ROLE_TECHNICIAN,
                    'phone': phone,
                }
            )
            u.set_password('tech1234')
            u.save()
            tp, created = TechnicianProfile.objects.get_or_create(
                user=u,
                defaults={
                    'full_name': full_name,
                    'phone': phone,
                    'bio': f"Certified professional with {exp} years of hands-on experience in doorstep repair services.",
                    'experience': exp,
                    'service_area': sarea,
                    'address': address,
                    'city': city,
                    'state': 'Andhra Pradesh',
                    'postal_code': '520001',
                    'latitude': lat,
                    'longitude': lon,
                    'estimated_cost_min': cmin,
                    'estimated_cost_max': cmax,
                    'verification_status': vstatus,
                    'availability_status': astatus,
                }
            )
            for sname in skills:
                sc = category_objs.get(sname)
                if sc:
                    TechnicianSkill.objects.get_or_create(technician=tp, service_category=sc)
            for d in days:
                Availability.objects.get_or_create(
                    technician=tp,
                    day_of_week=d,
                    defaults={
                        'is_available': True if d < 6 else (True if vstatus == TechnicianProfile.VERIFICATION_VERIFIED else False),
                        'start_time': '09:00',
                        'end_time': '19:00'
                    }
                )
            technician_profiles.append(tp)
        self.stdout.write(self.style.SUCCESS(f"[OK] {len(technician_profiles)} Technician profiles initialized. Password: tech1234"))

        sample_requests = [
            (customer_profiles[0], 'AC Repair', 'Samsung 1.5T Split AC', 'Not cooling enough. Compressor clicks on but airflow is warm.', 'Door 40-1-52, MG Road, Benz Circle', RepairRequest.URGENCY_HIGH),
            (customer_profiles[1], 'Washing Machine Repair', 'IFB Front Load Washing Machine 6.5kg', 'Drum not spinning during cycle. Water drains fine. Makes humming noise.', 'Flat 302, Sri Krishna Apts, Bhavanipuram', RepairRequest.URGENCY_MEDIUM),
            (customer_profiles[2], 'Mobile Repair', 'iPhone 13', 'Cracked front screen and battery drains very fast. Face ID still works.', 'House 12-4, Ring Road, Gunadala', RepairRequest.URGENCY_HIGH),
            (customer_profiles[3], 'Plumbing', 'Kitchen Sink & Wash Area', 'Persistent leakage under kitchen sink and slow drain in wash area.', 'Plot 88, Kaleswara Rao Market, Governorpet', RepairRequest.URGENCY_MEDIUM),
            (customer_profiles[0], 'Refrigerator Repair', 'LG Double Door 260L', 'Freezer section frosting heavily and lower section not cold enough.', 'Door 40-1-52, MG Road, Benz Circle', RepairRequest.URGENCY_HIGH),
        ]

        today = timezone.now().date()
        seeded_requests = []
        for idx, (cust, cat_name, device, problem, loc, urgency) in enumerate(sample_requests):
            sc = category_objs.get(cat_name)
            req, created = RepairRequest.objects.get_or_create(
                customer=cust,
                device_name=device,
                defaults={
                    'service_category': sc,
                    'problem_description': problem,
                    'location': loc,
                    'city': cust.city,
                    'latitude': cust.latitude,
                    'longitude': cust.longitude,
                    'urgency': urgency,
                    'preferred_date': today + timedelta(days=idx % 3),
                    'preferred_time': ['Morning 9-12', 'Afternoon 1-4', 'Evening 5-8'][idx % 3],
                    'budget': 650 + idx * 100,
                    'status': RepairRequest.STATUS_MATCHING,
                }
            )
            if created:
                find_and_rank_technicians(req)
            seeded_requests.append(req)
        self.stdout.write(self.style.SUCCESS(f"[OK] {len(seeded_requests)} Sample repair requests created with technician matches."))

        if seeded_requests and technician_profiles:
            demo_req = seeded_requests[0]
            verified = [t for t in technician_profiles if t.verification_status == TechnicianProfile.VERIFICATION_VERIFIED]
            if verified:
                demo_tech = verified[0]
                demo_req.selected_technician = demo_tech
                demo_req.status = RepairRequest.STATUS_TECHNICIAN_SELECTED
                demo_req.save()

                job, _ = Job.objects.get_or_create(
                    repair_request=demo_req,
                    defaults={
                        'technician': demo_tech,
                        'customer': demo_req.customer,
                        'status': Job.STATUS_ACCEPTED,
                        'notes': 'Initial inspection complete. Will proceed with diagnosis.',
                    }
                )
                JobStatusHistory.objects.get_or_create(
                    job=job, status=Job.STATUS_ACCEPTED,
                    defaults={'changed_by': demo_tech.user, 'note': 'Job accepted by technician.'}
                )

                job.transition_to(Job.STATUS_ON_THE_WAY, demo_tech.user, 'Technician left workshop with required spares.')
                job.transition_to(Job.STATUS_ARRIVED, demo_tech.user, 'Reached customer location. Greeted customer.')
                job.transition_to(Job.STATUS_IN_PROGRESS, demo_tech.user, 'Diagnosed compressor relay issue. Replaced capacitor and contactor.')

                job.transition_to(Job.STATUS_COMPLETED, demo_tech.user, 'Repair complete. AC now cools effectively.')
                job.final_cost = 1150.0
                job.save()

                Review.objects.get_or_create(
                    job=job,
                    defaults={
                        'customer': demo_req.customer,
                        'technician': demo_tech,
                        'rating': 5,
                        'comment': 'Excellent work! Suresh arrived on time, diagnosed the issue quickly and fixed our AC at a fair price. Highly recommended!'
                    }
                )
                demo_tech.update_rating_stats()
                self.stdout.write(self.style.SUCCESS("[OK] Demo job lifecycle with completed review created."))

        Complaint.objects.get_or_create(
            user=customer_profiles[1].user,
            defaults={
                'subject': 'Technician arrived late without intimation',
                'description': 'The assigned technician was expected by 10 AM but arrived after 3 PM with no prior call. Request rescheduling mechanism.',
                'status': Complaint.STATUS_IN_REVIEW,
                'admin_response': 'We regret the inconvenience and are implementing SMS alerts. This complaint is being investigated.',
            }
        )
        self.stdout.write(self.style.SUCCESS("[OK] Sample complaint created."))

        Notification.objects.bulk_create([
            Notification(user=customer_profiles[0].user, title='Welcome to RepairNow!', message='Start by browsing our services or raising a repair request.', link='/customer/dashboard/', notification_type='WELCOME'),
            Notification(user=customer_profiles[1].user, title='Welcome to RepairNow!', message='Book verified technicians in under 60 seconds.', link='/customer/dashboard/', notification_type='WELCOME'),
            Notification(user=technician_profiles[0].user, title='Profile Verified!', message='Your profile is now verified. You will receive repair requests shortly.', link='/technician/dashboard/', notification_type='VERIFICATION'),
        ], ignore_conflicts=True)
        self.stdout.write(self.style.SUCCESS("[OK] Welcome notifications seeded."))

        self.stdout.write(self.style.SUCCESS("\n==== SEEDING COMPLETE ===="))
        self.stdout.write("Admin:   admin / admin123")
        self.stdout.write("Customer accounts: ramesh_v, priya_s, ananya_p, vikram_r  |  pwd: user1234")
        self.stdout.write("Technician accounts: suresh_tech, naresh_ac, rajesh_washer, manoj_mobile, arun_plumber, pending_tech  |  pwd: tech1234")
