import io
from PIL import Image
from pathlib import Path

from decimal import Decimal
from django.test import TestCase, Client, override_settings
from django.conf import settings
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.exceptions import ValidationError
from datetime import timedelta
from accounts.models import CustomerProfile
from accounts.forms import CustomerRegistrationForm
from accounts.validators import validate_image_file, validate_document_file, MAX_UPLOAD_SIZE
from services.models import ServiceCategory
from technicians.models import TechnicianProfile, TechnicianSkill
from repairs.models import RepairRequest, Job, JobStatusHistory, TechnicianMatch, TechnicianRejection
from repairs.matching import haversine_distance, calculate_distance_score, calculate_cost_score, find_and_rank_technicians
from repairs.forms import RepairRequestForm
from reviews.models import Review, Complaint
from notifications.models import Notification
from django.core.cache import cache

User = get_user_model()


class RepairNowTestSuite(TestCase):
    def test_tracking_template_uses_check_and_cross_icons_not_technician_selected_label(self):
        template_text = Path('templates/customer/track.html').read_text(encoding='utf-8')

        self.assertNotIn('Technician Selected', template_text)
        self.assertIn('fa-check', template_text)
        self.assertIn('fa-xmark', template_text)

    def setUp(self):
        self.client = Client()

        self.cat_ac = ServiceCategory.objects.create(name='AC Repair', icon='fa-snowflake')
        self.cat_washer = ServiceCategory.objects.create(name='Washing Machine Repair', icon='fa-soap')

        self.cust_user1 = User.objects.create_user(username='cust1', password='password123', role=User.ROLE_CUSTOMER)
        self.cust_profile1 = CustomerProfile.objects.create(
            user=self.cust_user1, full_name='Customer One', phone='9876543210',
            address='MG Road', city='Vijayawada', latitude=16.5033, longitude=80.6465
        )

        self.cust_user2 = User.objects.create_user(username='cust2', password='password123', role=User.ROLE_CUSTOMER)
        self.cust_profile2 = CustomerProfile.objects.create(
            user=self.cust_user2, full_name='Customer Two', phone='9876543211',
            address='Bhavanipuram', city='Vijayawada', latitude=16.5180, longitude=80.6120
        )

        self.tech_user1 = User.objects.create_user(username='tech1', password='password123', role=User.ROLE_TECHNICIAN)
        self.tech_profile1 = TechnicianProfile.objects.create(
            user=self.tech_user1, full_name='Tech Suresh', phone='9849112233',
            experience=6, city='Vijayawada', latitude=16.5010, longitude=80.6420,
            estimated_cost_min=500, estimated_cost_max=1000,
            verification_status=TechnicianProfile.VERIFICATION_VERIFIED,
            availability_status=TechnicianProfile.AVAILABILITY_AVAILABLE
        )
        TechnicianSkill.objects.create(technician=self.tech_profile1, service_category=self.cat_ac)

        self.tech_user2 = User.objects.create_user(username='tech2', password='password123', role=User.ROLE_TECHNICIAN)
        self.tech_profile2 = TechnicianProfile.objects.create(
            user=self.tech_user2, full_name='Tech Unverified', phone='9849112234',
            experience=2, city='Vijayawada', latitude=16.5100, longitude=80.6250,
            verification_status=TechnicianProfile.VERIFICATION_PENDING,
            availability_status=TechnicianProfile.AVAILABILITY_AVAILABLE
        )
        TechnicianSkill.objects.create(technician=self.tech_profile2, service_category=self.cat_washer)

        self.tech_user3 = User.objects.create_user(username='tech3', password='password123', role=User.ROLE_TECHNICIAN)
        self.tech_profile3 = TechnicianProfile.objects.create(
            user=self.tech_user3, full_name='Tech Alternate', phone='9849112235',
            experience=4, city='Vijayawada', latitude=16.5020, longitude=80.6430,
            estimated_cost_min=600, estimated_cost_max=1200,
            verification_status=TechnicianProfile.VERIFICATION_VERIFIED,
            availability_status=TechnicianProfile.AVAILABILITY_AVAILABLE
        )
        TechnicianSkill.objects.create(technician=self.tech_profile3, service_category=self.cat_ac)

        self.admin_user = User.objects.create_superuser(username='admin_test', password='password123', role=User.ROLE_ADMIN)

    def test_default_service_categories_are_created_when_missing(self):
        ServiceCategory.objects.all().delete()

        created = ServiceCategory.ensure_default_categories()

        self.assertGreater(len(created), 0)
        self.assertTrue(ServiceCategory.objects.filter(is_active=True).exists())
        self.assertTrue(ServiceCategory.objects.filter(name='AC Repair').exists())

    def test_user_can_delete_notification(self):
        self.client.login(username='cust1', password='password123')
        notif = Notification.objects.create(
            user=self.cust_user1,
            title='Test notification',
            message='Delete me',
            link='/customer/dashboard/'
        )

        res = self.client.post(reverse('delete_notification', args=[notif.id]))

        self.assertEqual(res.status_code, 302)
        self.assertFalse(Notification.objects.filter(id=notif.id).exists())

    def test_customer_registration(self):
        res = self.client.post(reverse('register_customer'), {
            'username': 'new_cust',
            'email': 'new_cust@test.com',
            'full_name': 'New Customer',
            'phone': '9898989898',
            'address': 'Street 1',
            'city': 'Vijayawada',
            'state': 'Andhra Pradesh',
            'postal_code': '520001',
            'password': 'secretpassword',
            'confirm_password': 'secretpassword',
        })
        self.assertEqual(res.status_code, 302)
        self.assertTrue(User.objects.filter(username='new_cust', role=User.ROLE_CUSTOMER).exists())
        self.assertTrue(CustomerProfile.objects.filter(user__username='new_cust').exists())

    def test_technician_registration(self):
        res = self.client.post(reverse('register_technician'), {
            'username': 'new_tech',
            'email': 'new_tech@test.com',
            'full_name': 'New Tech',
            'phone': '9191919191',
            'experience': 4,
            'service_area': 'Central Zone',
            'address': 'Workshop 2',
            'city': 'Vijayawada',
            'state': 'Andhra Pradesh',
            'skills': [self.cat_ac.id],
            'estimated_cost_min': 400,
            'estimated_cost_max': 800,
            'password': 'techpassword',
            'confirm_password': 'techpassword',
        })

        self.assertEqual(res.status_code, 302)
        tech_user = User.objects.filter(username='new_tech', role=User.ROLE_TECHNICIAN).first()
        self.assertIsNotNone(tech_user)
        self.assertEqual(tech_user.technician_profile.verification_status, TechnicianProfile.VERIFICATION_PENDING)

    def test_login_and_logout(self):
        login_res = self.client.post(reverse('login'), {'username': 'cust1', 'password': 'password123'})
        self.assertEqual(login_res.status_code, 302)

        logout_res = self.client.post(reverse('logout'))
        self.assertEqual(logout_res.status_code, 302)

        bad_login = self.client.post(reverse('login'), {'username': 'cust1', 'password': 'wrongpassword'})
        self.assertEqual(bad_login.status_code, 200)
        self.assertContains(bad_login, "Invalid username or password")

    def test_customer_cannot_access_technician_dashboard(self):
        self.client.login(username='cust1', password='password123')
        res = self.client.get(reverse('technician_dashboard'))
        self.assertEqual(res.status_code, 302)

    def test_technician_cannot_access_admin_dashboard(self):
        self.client.login(username='tech1', password='password123')
        res = self.client.get(reverse('admin_dashboard'))
        self.assertEqual(res.status_code, 302)

    def test_customer_cannot_access_other_customer_request(self):
        req = RepairRequest.objects.create(
            customer=self.cust_profile1, service_category=self.cat_ac,
            device_name='Split AC', problem_description='Not turning on',
            location='MG Road', city='Vijayawada', urgency=RepairRequest.URGENCY_MEDIUM,
            preferred_date=timezone.now().date(), preferred_time='Morning'
        )
        self.client.login(username='cust2', password='password123')
        res = self.client.get(reverse('customer_repair_detail', args=[req.id]))
        self.assertEqual(res.status_code, 403)

    def test_repair_request_creation_and_matching(self):
        self.client.login(username='cust1', password='password123')
        res = self.client.post(reverse('customer_repair_create'), {
            'service_category': self.cat_ac.id,
            'device_name': 'Daikin Inverter AC',
            'problem_description': 'Cooling fan not spinning',
            'location': 'Benz Circle',
            'city': 'Vijayawada',
            'urgency': RepairRequest.URGENCY_HIGH,
            'preferred_date': timezone.now().date().strftime('%Y-%m-%d'),
            'preferred_time': 'Morning',
            'budget': 800,
        })
        self.assertEqual(res.status_code, 302)
        req = RepairRequest.objects.filter(device_name='Daikin Inverter AC').first()
        self.assertIsNotNone(req)
        self.assertTrue(req.matches.exists())

    def test_request_validation_past_date(self):
        self.client.login(username='cust1', password='password123')
        past_date = (timezone.now().date() - timedelta(days=2)).strftime('%Y-%m-%d')
        res = self.client.post(reverse('customer_repair_create'), {
            'service_category': self.cat_ac.id,
            'device_name': 'AC',
            'problem_description': 'Issue',
            'location': 'Address',
            'city': 'Vijayawada',
            'urgency': 'MEDIUM',
            'preferred_date': past_date,
            'preferred_time': 'Morning',
            'budget': 500,
        })
        self.assertContains(res, "Preferred date cannot be in the past.")

    def test_matching_filters_unverified_technicians(self):
        req = RepairRequest.objects.create(
            customer=self.cust_profile1, service_category=self.cat_washer,
            device_name='Washer Machine', problem_description='Drum issue',
            location='MG Road', city='Vijayawada', urgency=RepairRequest.URGENCY_MEDIUM,
            preferred_date=timezone.now().date(), preferred_time='Morning'
        )
        matches = find_and_rank_technicians(req)
        self.assertEqual(len(matches), 0)

    def test_haversine_distance_calculation(self):
        dist = haversine_distance(16.5033, 80.6465, 16.5180, 80.6120)
        self.assertGreater(dist, 3.5)
        self.assertLess(dist, 4.5)

    def test_cost_compatibility_score(self):
        score_in_range = calculate_cost_score(self.tech_profile1, 750)
        self.assertEqual(score_in_range, 100.0)

        score_below_range = calculate_cost_score(self.tech_profile1, 300)
        self.assertLess(score_below_range, 100.0)

    def test_technician_job_lifecycle(self):
        req = RepairRequest.objects.create(
            customer=self.cust_profile1, service_category=self.cat_ac,
            device_name='Split AC', problem_description='Coil leak',
            location='MG Road', city='Vijayawada', urgency=RepairRequest.URGENCY_HIGH,
            preferred_date=timezone.now().date(), preferred_time='Morning',
            selected_technician=self.tech_profile1,
            status=RepairRequest.STATUS_TECHNICIAN_SELECTED
        )

        self.client.login(username='tech1', password='password123')
        accept_res = self.client.post(reverse('technician_accept_request', args=[req.id]))
        self.assertEqual(accept_res.status_code, 302)

        job = Job.objects.filter(repair_request=req).first()
        self.assertIsNotNone(job)
        self.assertEqual(job.status, Job.STATUS_ACCEPTED)

        self.client.post(reverse('technician_update_job_status', args=[job.id]), {'status': Job.STATUS_ON_THE_WAY})
        job.refresh_from_db()
        self.assertEqual(job.status, Job.STATUS_ON_THE_WAY)

        self.client.post(reverse('technician_update_job_status', args=[job.id]), {'status': Job.STATUS_ARRIVED})
        job.refresh_from_db()
        self.assertEqual(job.status, Job.STATUS_ARRIVED)

        self.client.post(reverse('technician_update_job_status', args=[job.id]), {'status': Job.STATUS_IN_PROGRESS})
        job.refresh_from_db()
        self.assertEqual(job.status, Job.STATUS_IN_PROGRESS)

        self.client.post(reverse('technician_update_job_status', args=[job.id]), {
            'status': Job.STATUS_COMPLETED,
            'final_cost': '650.00',
            'notes': 'Fixed coil and charged gas'
        })
        job.refresh_from_db()
        self.assertEqual(job.status, Job.STATUS_COMPLETED)
        self.assertEqual(float(job.final_cost), 650.0)

    def test_review_validation_and_average_update(self):
        req = RepairRequest.objects.create(
            customer=self.cust_profile1, service_category=self.cat_ac,
            device_name='AC Unit', problem_description='Noise',
            location='MG Road', city='Vijayawada', urgency=RepairRequest.URGENCY_MEDIUM,
            preferred_date=timezone.now().date(), preferred_time='Morning',
            selected_technician=self.tech_profile1, status=RepairRequest.STATUS_COMPLETED
        )
        job = Job.objects.create(
            repair_request=req, technician=self.tech_profile1,
            customer=self.cust_profile1, status=Job.STATUS_COMPLETED,
            final_cost=700.0, completed_date=timezone.now()
        )

        self.client.login(username='cust1', password='password123')
        res = self.client.post(reverse('submit_review', args=[job.id]), {
            'rating': 5,
            'comment': 'Outstanding repair and courteous technician!',
        })
        self.assertEqual(res.status_code, 302)

        rev = Review.objects.filter(job=job).first()
        self.assertIsNotNone(rev)
        self.assertEqual(rev.rating, 5)

        self.tech_profile1.refresh_from_db()
        self.assertEqual(self.tech_profile1.average_rating, 5.0)
        self.assertEqual(self.tech_profile1.total_reviews_count, 1)

        dup_res = self.client.post(reverse('submit_review', args=[job.id]), {
            'rating': 4,
            'comment': 'Duplicate attempt',
        })
        self.assertEqual(dup_res.status_code, 302)
        self.assertEqual(Review.objects.filter(job=job).count(), 1)

    def test_customer_select_technician_rejects_get_requests(self):
        req = RepairRequest.objects.create(
            customer=self.cust_profile1, service_category=self.cat_ac,
            device_name='Split AC', problem_description='No cooling',
            location='Benz Circle', city='Vijayawada', urgency=RepairRequest.URGENCY_MEDIUM,
            preferred_date=timezone.now().date(), preferred_time='Morning',
            status=RepairRequest.STATUS_MATCHING
        )
        TechnicianMatch.objects.create(repair_request=req, technician=self.tech_profile1, match_score=95.0)

        self.client.login(username='cust1', password='password123')
        get_res = self.client.get(reverse('customer_select_technician', args=[req.id, self.tech_profile1.id]))
        # Must reject GET with 405 Method Not Allowed
        self.assertEqual(get_res.status_code, 405)

    def test_customer_select_technician_enforces_ownership(self):
        req = RepairRequest.objects.create(
            customer=self.cust_profile1, service_category=self.cat_ac,
            device_name='Split AC', problem_description='No cooling',
            location='Benz Circle', city='Vijayawada', urgency=RepairRequest.URGENCY_MEDIUM,
            preferred_date=timezone.now().date(), preferred_time='Morning',
            status=RepairRequest.STATUS_MATCHING
        )
        TechnicianMatch.objects.create(repair_request=req, technician=self.tech_profile1, match_score=95.0)

        # Login as customer 2 (different customer)
        self.client.login(username='cust2', password='password123')
        post_res = self.client.post(reverse('customer_select_technician', args=[req.id, self.tech_profile1.id]))
        self.assertEqual(post_res.status_code, 403)

    def test_customer_select_technician_enforces_lifecycle_status(self):
        req = RepairRequest.objects.create(
            customer=self.cust_profile1, service_category=self.cat_ac,
            device_name='Split AC', problem_description='No cooling',
            location='Benz Circle', city='Vijayawada', urgency=RepairRequest.URGENCY_MEDIUM,
            preferred_date=timezone.now().date(), preferred_time='Morning',
            status=RepairRequest.STATUS_ACCEPTED, selected_technician=self.tech_profile1
        )
        TechnicianMatch.objects.create(repair_request=req, technician=self.tech_profile1, match_score=95.0)

        self.client.login(username='cust1', password='password123')
        post_res = self.client.post(reverse('customer_select_technician', args=[req.id, self.tech_profile1.id]))
        self.assertEqual(post_res.status_code, 302)
        req.refresh_from_db()
        # Status must remain ACCEPTED, not modified
        self.assertEqual(req.status, RepairRequest.STATUS_ACCEPTED)

    def test_customer_select_technician_requires_technician_match(self):
        req = RepairRequest.objects.create(
            customer=self.cust_profile1, service_category=self.cat_ac,
            device_name='Split AC', problem_description='No cooling',
            location='Benz Circle', city='Vijayawada', urgency=RepairRequest.URGENCY_MEDIUM,
            preferred_date=timezone.now().date(), preferred_time='Morning',
            status=RepairRequest.STATUS_MATCHING
        )
        # Tech 1 is NOT added to req.matches

        self.client.login(username='cust1', password='password123')
        post_res = self.client.post(reverse('customer_select_technician', args=[req.id, self.tech_profile1.id]))
        self.assertEqual(post_res.status_code, 302)
        req.refresh_from_db()
        self.assertIsNone(req.selected_technician)
        self.assertEqual(req.status, RepairRequest.STATUS_MATCHING)

    def test_customer_select_technician_success(self):
        req = RepairRequest.objects.create(
            customer=self.cust_profile1, service_category=self.cat_ac,
            device_name='Split AC', problem_description='No cooling',
            location='Benz Circle', city='Vijayawada', urgency=RepairRequest.URGENCY_MEDIUM,
            preferred_date=timezone.now().date(), preferred_time='Morning',
            status=RepairRequest.STATUS_MATCHING
        )
        TechnicianMatch.objects.create(repair_request=req, technician=self.tech_profile1, match_score=95.0)

        self.client.login(username='cust1', password='password123')
        post_res = self.client.post(reverse('customer_select_technician', args=[req.id, self.tech_profile1.id]))
        self.assertEqual(post_res.status_code, 302)
        req.refresh_from_db()
        self.assertEqual(req.selected_technician, self.tech_profile1)
        self.assertEqual(req.status, RepairRequest.STATUS_TECHNICIAN_SELECTED)

    def test_technician_rejection_creates_history_and_deletes_match(self):
        req = RepairRequest.objects.create(
            customer=self.cust_profile1, service_category=self.cat_ac,
            device_name='Split AC', problem_description='No cooling',
            location='Benz Circle', city='Vijayawada', urgency=RepairRequest.URGENCY_MEDIUM,
            preferred_date=timezone.now().date(), preferred_time='Morning',
            selected_technician=self.tech_profile1,
            status=RepairRequest.STATUS_TECHNICIAN_SELECTED
        )
        match = TechnicianMatch.objects.create(repair_request=req, technician=self.tech_profile1, match_score=95.0)

        self.client.login(username='tech1', password='password123')
        reject_res = self.client.post(reverse('technician_reject_request', args=[req.id]))
        self.assertEqual(reject_res.status_code, 302)

        req.refresh_from_db()
        self.assertEqual(req.status, RepairRequest.STATUS_REJECTED)
        self.assertIsNone(req.selected_technician)

        # Verify persistent rejection record exists
        rejection_exists = TechnicianRejection.objects.filter(repair_request=req, technician=self.tech_profile1).exists()
        self.assertTrue(rejection_exists)

        # Verify technician match record was deleted
        self.assertFalse(TechnicianMatch.objects.filter(repair_request=req, technician=self.tech_profile1).exists())

        # Customer attempts to re-select the rejected technician
        self.client.login(username='cust1', password='password123')
        reselect_res = self.client.post(reverse('customer_select_technician', args=[req.id, self.tech_profile1.id]))
        self.assertEqual(reselect_res.status_code, 302)
        req.refresh_from_db()
        self.assertIsNone(req.selected_technician)
        self.assertEqual(req.status, RepairRequest.STATUS_REJECTED)

    def test_customer_matches_template_uses_post_form_with_csrf(self):
        template_text = Path('templates/customer/matches.html').read_text(encoding='utf-8')
        self.assertIn('form method="post"', template_text)
        self.assertIn('csrf_token', template_text)
        self.assertIn('customer_select_technician', template_text)

    def test_rejected_request_appears_on_customer_dashboard_and_can_select_alternate_tech(self):
        req = RepairRequest.objects.create(
            customer=self.cust_profile1, service_category=self.cat_ac,
            device_name='Split AC', problem_description='No cooling',
            location='Benz Circle', city='Vijayawada', urgency=RepairRequest.URGENCY_MEDIUM,
            preferred_date=timezone.now().date(), preferred_time='Morning',
            status=RepairRequest.STATUS_REJECTED
        )
        # tech1 previously rejected
        TechnicianRejection.objects.create(repair_request=req, technician=self.tech_profile1)
        # tech3 is an eligible match
        TechnicianMatch.objects.create(repair_request=req, technician=self.tech_profile3, match_score=92.0)

        self.client.login(username='cust1', password='password123')
        res = self.client.get(reverse('customer_dashboard'))
        self.assertEqual(res.status_code, 200)
        self.assertIn(req, res.context['active_requests'])
        self.assertGreaterEqual(res.context['pending_count'], 1)
        self.assertContains(res, 'Declined / Needs Tech')

        # Customer views matches
        match_res = self.client.get(reverse('customer_repair_matches', args=[req.id]))
        self.assertEqual(match_res.status_code, 200)

        # Customer attempts to select the rejected tech1 - must fail
        post_reject = self.client.post(reverse('customer_select_technician', args=[req.id, self.tech_profile1.id]))
        self.assertEqual(post_reject.status_code, 302)
        req.refresh_from_db()
        self.assertIsNone(req.selected_technician)
        self.assertEqual(req.status, RepairRequest.STATUS_REJECTED)

        # Customer selects eligible alternate tech3 - must succeed
        post_alt = self.client.post(reverse('customer_select_technician', args=[req.id, self.tech_profile3.id]))
        self.assertEqual(post_alt.status_code, 302)
        req.refresh_from_db()
        self.assertEqual(req.selected_technician, self.tech_profile3)
        self.assertEqual(req.status, RepairRequest.STATUS_TECHNICIAN_SELECTED)

    def test_rejected_request_visibility_on_technician_dashboard_and_requests(self):
        req = RepairRequest.objects.create(
            customer=self.cust_profile1, service_category=self.cat_ac,
            device_name='Split AC', problem_description='Compressor issue',
            location='Benz Circle', city='Vijayawada', urgency=RepairRequest.URGENCY_MEDIUM,
            preferred_date=timezone.now().date(), preferred_time='Morning',
            status=RepairRequest.STATUS_REJECTED
        )
        TechnicianRejection.objects.create(repair_request=req, technician=self.tech_profile1)

        self.client.login(username='tech1', password='password123')

        # 1. Technician Dashboard: rejected request should NOT appear in new_requests, but count is tracked
        dash_res = self.client.get(reverse('technician_dashboard'))
        self.assertEqual(dash_res.status_code, 200)
        self.assertNotIn(req, dash_res.context['new_requests'])
        self.assertEqual(dash_res.context['declined_requests_count'], 1)
        self.assertContains(dash_res, 'Declined Requests')

        # 2. Technician Requests: rejected request appears in history
        reqs_res = self.client.get(reverse('technician_requests'))
        self.assertEqual(reqs_res.status_code, 200)
        self.assertIn(req, reqs_res.context['requests'])
        self.assertContains(reqs_res, 'You declined this request')

        # 3. Technician Request Detail: can view request details with decline banner
        detail_res = self.client.get(reverse('technician_request_detail', args=[req.id]))
        self.assertEqual(detail_res.status_code, 200)
        self.assertEqual(detail_res.context['repair_request'], req)
        self.assertContains(detail_res, 'Request Declined')
        self.assertContains(detail_res, 'Declined (No further action)')

    def test_login_open_redirect_safe_local_next(self):
        res = self.client.post(reverse('login') + '?next=/customer/history/', {
            'username': 'cust1',
            'password': 'password123',
        })
        self.assertRedirects(res, '/customer/history/')

    def test_login_open_redirect_rejects_external_target(self):
        res = self.client.post(reverse('login') + '?next=https://attacker.example.com/phishing', {
            'username': 'cust1',
            'password': 'password123',
        })
        self.assertRedirects(res, reverse('login_redirect'), target_status_code=302)

    def test_login_works_without_next(self):
        res = self.client.post(reverse('login'), {
            'username': 'cust1',
            'password': 'password123',
        })
        self.assertRedirects(res, reverse('login_redirect'), target_status_code=302)

    def test_complaint_idor_protection(self):
        req = RepairRequest.objects.create(
            customer=self.cust_profile1, service_category=self.cat_ac,
            device_name='Split AC', problem_description='No cooling',
            location='Benz Circle', city='Vijayawada', urgency=RepairRequest.URGENCY_MEDIUM,
            preferred_date=timezone.now().date(), preferred_time='Morning',
            status=RepairRequest.STATUS_ACCEPTED, selected_technician=self.tech_profile1
        )
        job = Job.objects.create(
            repair_request=req, customer=self.cust_profile1, technician=self.tech_profile1,
            status=Job.STATUS_ACCEPTED
        )

        # 1. Job customer can access and complain
        self.client.login(username='cust1', password='password123')
        get_res = self.client.get(reverse('submit_complaint_job', args=[job.id]))
        self.assertEqual(get_res.status_code, 200)
        post_res = self.client.post(reverse('submit_complaint_job', args=[job.id]), {
            'subject': 'Delay',
            'description': 'Technician arrived late',
        })
        self.assertEqual(post_res.status_code, 302)
        self.assertTrue(Complaint.objects.filter(job=job, user=self.cust_user1).exists())

        # 2. Job technician can access and complain
        self.client.login(username='tech1', password='password123')
        get_tech = self.client.get(reverse('submit_complaint_job', args=[job.id]))
        self.assertEqual(get_tech.status_code, 200)
        post_tech = self.client.post(reverse('submit_complaint_job', args=[job.id]), {
            'subject': 'Access Issue',
            'description': 'Customer was unavailable at scheduled time',
        })
        self.assertEqual(post_tech.status_code, 302)
        self.assertTrue(Complaint.objects.filter(job=job, user=self.tech_user1).exists())

        # 3. Unrelated customer cannot access or complain (403 Forbidden)
        self.client.login(username='cust2', password='password123')
        get_unrelated_cust = self.client.get(reverse('submit_complaint_job', args=[job.id]))
        self.assertEqual(get_unrelated_cust.status_code, 403)
        post_unrelated_cust = self.client.post(reverse('submit_complaint_job', args=[job.id]), {
            'subject': 'Unauthorized',
            'description': 'Trying to complain on job I do not own',
        })
        self.assertEqual(post_unrelated_cust.status_code, 403)
        self.assertFalse(Complaint.objects.filter(job=job, user=self.cust_user2).exists())

        # 4. Unrelated technician cannot access or complain (403 Forbidden)
        self.client.login(username='tech3', password='password123')
        get_unrelated_tech = self.client.get(reverse('submit_complaint_job', args=[job.id]))
        self.assertEqual(get_unrelated_tech.status_code, 403)
        post_unrelated_tech = self.client.post(reverse('submit_complaint_job', args=[job.id]), {
            'subject': 'Unauthorized Tech',
            'description': 'Trying to complain on job I am not assigned to',
        })
        self.assertEqual(post_unrelated_tech.status_code, 403)
        self.assertFalse(Complaint.objects.filter(job=job, user=self.tech_user3).exists())

        # 5. Authorized admin can access
        self.client.login(username='admin_test', password='password123')
        get_admin = self.client.get(reverse('submit_complaint_job', args=[job.id]))
        self.assertEqual(get_admin.status_code, 200)

    def test_admin_toggle_user_active_security(self):
        # 1. GET returns 405 Method Not Allowed
        self.client.login(username='admin_test', password='password123')
        get_res = self.client.get(reverse('admin_toggle_user_active', args=[self.cust_user2.id]))
        self.assertEqual(get_res.status_code, 405)

        # 2. POST without valid CSRF fails
        csrf_client = Client(enforce_csrf_checks=True)
        csrf_client.login(username='admin_test', password='password123')
        csrf_res = csrf_client.post(reverse('admin_toggle_user_active', args=[self.cust_user2.id]))
        self.assertEqual(csrf_res.status_code, 403)

        # 3. Non-admin users cannot perform the action
        self.client.login(username='cust1', password='password123')
        non_admin_res = self.client.post(reverse('admin_toggle_user_active', args=[self.cust_user2.id]))
        self.assertEqual(non_admin_res.status_code, 302)
        self.cust_user2.refresh_from_db()
        self.assertTrue(self.cust_user2.is_active)

        # 4. Authorized admin POST succeeds and toggles active state
        self.client.login(username='admin_test', password='password123')
        admin_post = self.client.post(reverse('admin_toggle_user_active', args=[self.cust_user2.id]))
        self.assertEqual(admin_post.status_code, 302)
        self.cust_user2.refresh_from_db()
        self.assertFalse(self.cust_user2.is_active)

        # 5. Admin toggling again reactivates
        admin_post2 = self.client.post(reverse('admin_toggle_user_active', args=[self.cust_user2.id]))
        self.assertEqual(admin_post2.status_code, 302)
        self.cust_user2.refresh_from_db()
        self.assertTrue(self.cust_user2.is_active)

    def test_admin_verify_technician_security(self):
        # 1. GET returns 405 Method Not Allowed
        self.client.login(username='admin_test', password='password123')
        get_res = self.client.get(reverse('admin_verify_technician', args=[self.tech_profile2.id, 'approve']))
        self.assertEqual(get_res.status_code, 405)

        # 2. POST without valid CSRF fails
        csrf_client = Client(enforce_csrf_checks=True)
        csrf_client.login(username='admin_test', password='password123')
        csrf_res = csrf_client.post(reverse('admin_verify_technician', args=[self.tech_profile2.id, 'approve']))
        self.assertEqual(csrf_res.status_code, 403)

        # 3. Non-admin users cannot perform the action
        self.client.login(username='cust1', password='password123')
        non_admin_res = self.client.post(reverse('admin_verify_technician', args=[self.tech_profile2.id, 'approve']))
        self.assertEqual(non_admin_res.status_code, 302)
        self.tech_profile2.refresh_from_db()
        self.assertEqual(self.tech_profile2.verification_status, TechnicianProfile.VERIFICATION_PENDING)

        # 4. Authorized admin can approve
        self.client.login(username='admin_test', password='password123')
        approve_res = self.client.post(reverse('admin_verify_technician', args=[self.tech_profile2.id, 'approve']))
        self.assertEqual(approve_res.status_code, 302)
        self.tech_profile2.refresh_from_db()
        self.assertEqual(self.tech_profile2.verification_status, TechnicianProfile.VERIFICATION_VERIFIED)

        # 5. Authorized admin can reject
        reject_res = self.client.post(reverse('admin_verify_technician', args=[self.tech_profile2.id, 'reject']))
        self.assertEqual(reject_res.status_code, 302)
        self.tech_profile2.refresh_from_db()
        self.assertEqual(self.tech_profile2.verification_status, TechnicianProfile.VERIFICATION_REJECTED)

        # 6. Authorized admin can suspend
        suspend_res = self.client.post(reverse('admin_verify_technician', args=[self.tech_profile2.id, 'suspend']))
        self.assertEqual(suspend_res.status_code, 302)
        self.tech_profile2.refresh_from_db()
        self.assertEqual(self.tech_profile2.verification_status, TechnicianProfile.VERIFICATION_SUSPENDED)

        # 7. External malicious HTTP_REFERER cannot cause external redirect
        evil_ref_res = self.client.post(
            reverse('admin_verify_technician', args=[self.tech_profile2.id, 'approve']),
            HTTP_REFERER='https://evil.attacker.com/malware'
        )
        self.assertEqual(evil_ref_res.status_code, 302)
        self.assertRedirects(evil_ref_res, reverse('admin_technicians'))

        # 8. Local safe HTTP_REFERER redirects back to the safe local URL
        safe_ref_res = self.client.post(
            reverse('admin_verify_technician', args=[self.tech_profile2.id, 'approve']),
            HTTP_REFERER='http://testserver/admin/verifications/'
        )
        self.assertEqual(safe_ref_res.status_code, 302)
        self.assertRedirects(safe_ref_res, 'http://testserver/admin/verifications/')

    def test_technician_accept_request_security(self):
        # Setup repair request with tech1 selected
        repair_req = RepairRequest.objects.create(
            customer=self.cust_profile1,
            service_category=self.cat_ac,
            device_name='AC Unit',
            problem_description='Not cooling',
            location='MG Road',
            city='Vijayawada',
            preferred_date=timezone.now().date(),
            urgency=RepairRequest.URGENCY_MEDIUM,
            status=RepairRequest.STATUS_TECHNICIAN_SELECTED,
            selected_technician=self.tech_profile1,
        )
        TechnicianMatch.objects.create(repair_request=repair_req, technician=self.tech_profile1, match_score=95.0)

        # 1. GET returns 405 Method Not Allowed
        self.client.login(username='tech1', password='password123')
        get_res = self.client.get(reverse('technician_accept_request', args=[repair_req.id]))
        self.assertEqual(get_res.status_code, 405)

        # 2. POST without CSRF returns 403 Forbidden with CSRF enforcement
        csrf_client = Client(enforce_csrf_checks=True)
        csrf_client.login(username='tech1', password='password123')
        csrf_res = csrf_client.post(reverse('technician_accept_request', args=[repair_req.id]))
        self.assertEqual(csrf_res.status_code, 403)

        # 3. Unauthorized technician (tech2) gets 403 Forbidden
        self.client.login(username='tech2', password='password123')
        unauth_res = self.client.post(reverse('technician_accept_request', args=[repair_req.id]))
        self.assertEqual(unauth_res.status_code, 403)

        # 4. Authorized technician (tech1) POST succeeds
        self.client.login(username='tech1', password='password123')
        post_res = self.client.post(reverse('technician_accept_request', args=[repair_req.id]))
        self.assertEqual(post_res.status_code, 302)
        repair_req.refresh_from_db()
        self.assertEqual(repair_req.status, RepairRequest.STATUS_ACCEPTED)

        job = Job.objects.filter(repair_request=repair_req).first()
        self.assertIsNotNone(job)
        self.assertEqual(job.technician, self.tech_profile1)
        self.assertEqual(job.customer, self.cust_profile1)
        self.assertEqual(job.status, Job.STATUS_ACCEPTED)

        # 5. Duplicate acceptance fails safely and doesn't create duplicate Job
        post_res_dup = self.client.post(reverse('technician_accept_request', args=[repair_req.id]))
        self.assertEqual(post_res_dup.status_code, 302)
        self.assertEqual(Job.objects.filter(repair_request=repair_req).count(), 1)

    def test_technician_reject_request_security(self):
        # Setup repair request with tech1 selected
        repair_req = RepairRequest.objects.create(
            customer=self.cust_profile1,
            service_category=self.cat_ac,
            device_name='AC Unit 2',
            problem_description='Not cooling at all',
            location='MG Road',
            city='Vijayawada',
            preferred_date=timezone.now().date(),
            urgency=RepairRequest.URGENCY_MEDIUM,
            status=RepairRequest.STATUS_TECHNICIAN_SELECTED,
            selected_technician=self.tech_profile1,
        )
        TechnicianMatch.objects.create(repair_request=repair_req, technician=self.tech_profile1, match_score=90.0)

        # 1. GET returns 405 Method Not Allowed
        self.client.login(username='tech1', password='password123')
        get_res = self.client.get(reverse('technician_reject_request', args=[repair_req.id]))
        self.assertEqual(get_res.status_code, 405)

        # 2. POST without CSRF returns 403 Forbidden with CSRF enforcement
        csrf_client = Client(enforce_csrf_checks=True)
        csrf_client.login(username='tech1', password='password123')
        csrf_res = csrf_client.post(reverse('technician_reject_request', args=[repair_req.id]))
        self.assertEqual(csrf_res.status_code, 403)

        # 3. Unauthorized technician (tech2) gets 403 Forbidden
        self.client.login(username='tech2', password='password123')
        unauth_res = self.client.post(reverse('technician_reject_request', args=[repair_req.id]))
        self.assertEqual(unauth_res.status_code, 403)

        # 4. Authorized technician (tech1) POST succeeds
        self.client.login(username='tech1', password='password123')
        post_res = self.client.post(reverse('technician_reject_request', args=[repair_req.id]))
        self.assertEqual(post_res.status_code, 302)

        repair_req.refresh_from_db()
        self.assertIsNone(repair_req.selected_technician)
        self.assertEqual(repair_req.status, RepairRequest.STATUS_REJECTED)

        # Verify rejection history was created
        self.assertTrue(TechnicianRejection.objects.filter(repair_request=repair_req, technician=self.tech_profile1).exists())

        # Verify TechnicianMatch for rejected technician was removed
        self.assertFalse(TechnicianMatch.objects.filter(repair_request=repair_req, technician=self.tech_profile1).exists())

    def test_customer_repair_cancel_security(self):
        # Setup pending repair request owned by cust1
        repair_req = RepairRequest.objects.create(
            customer=self.cust_profile1,
            service_category=self.cat_ac,
            device_name='AC Unit 3',
            problem_description='Strange noise',
            location='MG Road',
            city='Vijayawada',
            preferred_date=timezone.now().date(),
            urgency=RepairRequest.URGENCY_LOW,
            status=RepairRequest.STATUS_PENDING,
        )

        # 1. GET returns 405 Method Not Allowed
        self.client.login(username='cust1', password='password123')
        get_res = self.client.get(reverse('customer_repair_cancel', args=[repair_req.id]))
        self.assertEqual(get_res.status_code, 405)

        # 2. POST without CSRF returns 403 Forbidden with CSRF enforcement
        csrf_client = Client(enforce_csrf_checks=True)
        csrf_client.login(username='cust1', password='password123')
        csrf_res = csrf_client.post(reverse('customer_repair_cancel', args=[repair_req.id]))
        self.assertEqual(csrf_res.status_code, 403)

        # 3. Unauthorized customer (cust2) gets 403 Forbidden
        self.client.login(username='cust2', password='password123')
        unauth_res = self.client.post(reverse('customer_repair_cancel', args=[repair_req.id]))
        self.assertEqual(unauth_res.status_code, 403)

        # 4. Authorized customer (cust1) POST succeeds
        self.client.login(username='cust1', password='password123')
        post_res = self.client.post(reverse('customer_repair_cancel', args=[repair_req.id]))
        self.assertEqual(post_res.status_code, 302)
        repair_req.refresh_from_db()
        self.assertEqual(repair_req.status, RepairRequest.STATUS_CANCELLED)

        # 5. Cannot cancel a completed request
        completed_req = RepairRequest.objects.create(
            customer=self.cust_profile1,
            service_category=self.cat_ac,
            device_name='AC Unit 4',
            problem_description='Completed job',
            location='MG Road',
            city='Vijayawada',
            preferred_date=timezone.now().date(),
            urgency=RepairRequest.URGENCY_LOW,
            status=RepairRequest.STATUS_COMPLETED,
        )
        cancel_completed_res = self.client.post(reverse('customer_repair_cancel', args=[completed_req.id]))
        self.assertEqual(cancel_completed_res.status_code, 302)
        completed_req.refresh_from_db()
        self.assertEqual(completed_req.status, RepairRequest.STATUS_COMPLETED)

    def test_file_upload_security(self):
        # 1. Create a helper valid JPEG
        img_byte_arr = io.BytesIO()
        image = Image.new('RGB', (20, 20), color='red')
        image.save(img_byte_arr, format='JPEG')
        valid_jpeg_bytes = img_byte_arr.getvalue()

        valid_jpeg = SimpleUploadedFile("test.jpg", valid_jpeg_bytes, content_type="image/jpeg")
        # Should not raise
        validate_image_file(valid_jpeg)

        # 2. Create a helper valid PNG
        img_png_arr = io.BytesIO()
        image_png = Image.new('RGB', (20, 20), color='blue')
        image_png.save(img_png_arr, format='PNG')
        valid_png_bytes = img_png_arr.getvalue()

        valid_png = SimpleUploadedFile("test.png", valid_png_bytes, content_type="image/png")
        validate_image_file(valid_png)

        # 3. Dangerous extensions rejected
        for bad_name in ["shell.html", "script.svg", "payload.exe", "virus.php", "code.js"]:
            bad_file = SimpleUploadedFile(bad_name, b"some content", content_type="text/plain")
            with self.assertRaises(ValidationError):
                validate_image_file(bad_file)

        # 4. Corrupt/fake image rejected even with .jpg extension
        fake_jpg = SimpleUploadedFile("fake.jpg", b"<?php phpinfo(); ?>", content_type="image/jpeg")
        with self.assertRaises(ValidationError):
            validate_image_file(fake_jpg)

        # 5. Oversized image rejected
        oversized_bytes = b"X" * (MAX_UPLOAD_SIZE + 1024)
        oversized_file = SimpleUploadedFile("huge.jpg", oversized_bytes, content_type="image/jpeg")
        with self.assertRaises(ValidationError):
            validate_image_file(oversized_file)

        # 6. Valid PDF document
        valid_pdf_bytes = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF"
        valid_pdf = SimpleUploadedFile("doc.pdf", valid_pdf_bytes, content_type="application/pdf")
        validate_document_file(valid_pdf)

        # 7. Fake PDF (missing %PDF- header) rejected
        fake_pdf = SimpleUploadedFile("fake.pdf", b"Not a real PDF", content_type="application/pdf")
        with self.assertRaises(ValidationError):
            validate_document_file(fake_pdf)

        # 8. Dangerous extension on document validator rejected
        bad_doc = SimpleUploadedFile("malware.exe", b"%PDF-fake", content_type="application/octet-stream")
        with self.assertRaises(ValidationError):
            validate_document_file(bad_doc)

        # 9. RepairRequestForm rejects fake image
        fake_img_upload = SimpleUploadedFile("fake.png", b"not an image data", content_type="image/png")
        form = RepairRequestForm(
            data={
                'service_category': self.cat_ac.id,
                'device_name': 'Test AC',
                'problem_description': 'Test description for validation',
                'location': 'Test Location',
                'city': 'Vijayawada',
                'urgency': RepairRequest.URGENCY_LOW,
                'preferred_date': timezone.now().date(),
            },
            files={'problem_image': fake_img_upload}
        )
        self.assertFalse(form.is_valid())
        self.assertIn('problem_image', form.errors)

    def test_admin_complaints_stored_xss_protection(self):
        # 1. Create a complaint with script and img onerror payloads in subject, description, and admin_response
        xss_payload = "<img src=x onerror=alert('xss-resp')><script>alert(1)</script>"
        complaint = Complaint.objects.create(
            user=self.cust_user1,
            subject="Billing <script>alert('xss-subj')</script>",
            description="Details <script>alert('xss-desc')</script>",
            admin_response=xss_payload,
            status=Complaint.STATUS_IN_REVIEW
        )
        empty_resp_complaint = Complaint.objects.create(
            user=self.cust_user1,
            subject="Empty response complaint",
            description="No reply yet",
            admin_response="",
            status=Complaint.STATUS_OPEN
        )

        self.client.login(username='admin_test', password='password123')
        res = self.client.get(reverse('admin_complaints'))
        self.assertEqual(res.status_code, 200)

        # 2. Verify malicious payload is escaped and not rendered unescaped as raw HTML
        self.assertNotContains(res, xss_payload)
        self.assertContains(res, "&lt;script&gt;alert(1)&lt;/script&gt;")
        self.assertContains(res, "&lt;img src=x onerror=alert(&#x27;xss-resp&#x27;)&gt;")
        self.assertContains(res, "&lt;script&gt;alert(&#x27;xss-desc&#x27;)&lt;/script&gt;")

        # 3. Verify clean fallback rendering when admin_response is empty
        self.assertContains(res, '<span style="color: var(--gray-400);">None</span>')

    def test_secure_logout(self):
        self.client.login(username='cust1', password='password123')

        # 1. GET logout returns 405 Method Not Allowed
        get_res = self.client.get(reverse('logout'))
        self.assertEqual(get_res.status_code, 405)

        # 2. POST without CSRF returns 403 Forbidden with CSRF enforcement
        csrf_client = Client(enforce_csrf_checks=True)
        csrf_client.login(username='cust1', password='password123')
        csrf_res = csrf_client.post(reverse('logout'))
        self.assertEqual(csrf_res.status_code, 403)

        # 3. Valid POST logs user out successfully
        post_res = self.client.post(reverse('logout'))
        self.assertEqual(post_res.status_code, 302)
        self.assertRedirects(post_res, reverse('home'))

        # Verify session is cleared and user is no longer authenticated
        self.assertNotIn('_auth_user_id', self.client.session)
        dash_res = self.client.get(reverse('customer_dashboard'))
        self.assertEqual(dash_res.status_code, 302)

    def test_secure_notification_state_changes(self):
        n1 = Notification.objects.create(
            user=self.cust_user1,
            title='Cust1 Notif',
            message='Message 1',
            is_read=False
        )
        n2 = Notification.objects.create(
            user=self.cust_user2,
            title='Cust2 Notif',
            message='Message 2',
            is_read=False
        )

        self.client.login(username='cust1', password='password123')

        # 1. GET mark_notification_read returns 405 Method Not Allowed
        get_res = self.client.get(reverse('mark_notification_read', args=[n1.id]))
        self.assertEqual(get_res.status_code, 405)

        # 2. GET mark_all_notifications_read returns 405 Method Not Allowed
        get_all_res = self.client.get(reverse('mark_all_notifications_read'))
        self.assertEqual(get_all_res.status_code, 405)

        # 3. POST without CSRF returns 403 with CSRF enforcement
        csrf_client = Client(enforce_csrf_checks=True)
        csrf_client.login(username='cust1', password='password123')
        csrf_res = csrf_client.post(reverse('mark_notification_read', args=[n1.id]))
        self.assertEqual(csrf_res.status_code, 403)

        # 4. Valid POST marks user's own notification as read
        post_res = self.client.post(reverse('mark_notification_read', args=[n1.id]))
        self.assertEqual(post_res.status_code, 302)
        n1.refresh_from_db()
        self.assertTrue(n1.is_read)

        # 5. User cannot modify another user's notification (404 Not Found)
        other_user_res = self.client.post(reverse('mark_notification_read', args=[n2.id]))
        self.assertEqual(other_user_res.status_code, 404)
        n2.refresh_from_db()
        self.assertFalse(n2.is_read)

        # 6. Mark all only marks current user's notifications
        n3 = Notification.objects.create(
            user=self.cust_user1,
            title='Cust1 Notif 2',
            message='Message 3',
            is_read=False
        )
        mark_all_res = self.client.post(reverse('mark_all_notifications_read'))
        self.assertEqual(mark_all_res.status_code, 302)
        n3.refresh_from_db()
        n2.refresh_from_db()
        self.assertTrue(n3.is_read)
        self.assertFalse(n2.is_read)

        # 7. AJAX POST works cleanly and returns JSON response
        n4 = Notification.objects.create(
            user=self.cust_user1,
            title='Cust1 Notif 3',
            message='Message 4',
            is_read=False
        )
        ajax_res = self.client.post(
            reverse('mark_notification_read', args=[n4.id]),
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        self.assertEqual(ajax_res.status_code, 200)
        self.assertEqual(ajax_res.json(), {'success': True, 'id': n4.id})
        n4.refresh_from_db()
        self.assertTrue(n4.is_read)

    def test_password_validation_and_rate_limiting(self):
        # 1. Weak passwords rejected in CustomerRegistrationForm
        # Short password (< 8 characters)
        form_short = CustomerRegistrationForm(data={
            'username': 'testshort',
            'email': 'short@test.com',
            'phone': '9876543210',
            'full_name': 'Test Short',
            'address': 'Street 1',
            'city': 'Vijayawada',
            'password': 'short',
            'confirm_password': 'short',
        })
        self.assertFalse(form_short.is_valid())
        self.assertIn('password', form_short.errors)

        # Numeric password
        form_num = CustomerRegistrationForm(data={
            'username': 'testnum',
            'email': 'num@test.com',
            'phone': '9876543210',
            'full_name': 'Test Num',
            'address': 'Street 1',
            'city': 'Vijayawada',
            'password': '12345678',
            'confirm_password': '12345678',
        })
        self.assertFalse(form_num.is_valid())
        self.assertIn('password', form_num.errors)

        # Common password
        form_com = CustomerRegistrationForm(data={
            'username': 'testcom',
            'email': 'com@test.com',
            'phone': '9876543210',
            'full_name': 'Test Com',
            'address': 'Street 1',
            'city': 'Vijayawada',
            'password': 'password',
            'confirm_password': 'password',
        })
        self.assertFalse(form_com.is_valid())
        self.assertIn('password', form_com.errors)

        # Strong password accepted
        form_strong = CustomerRegistrationForm(data={
            'username': 'teststrong',
            'email': 'strong@test.com',
            'phone': '9876543210',
            'full_name': 'Test Strong',
            'address': 'Street 1',
            'city': 'Vijayawada',
            'state': 'Andhra Pradesh',
            'password': 'StrongPass#2026!',
            'confirm_password': 'StrongPass#2026!',
        })
        self.assertTrue(form_strong.is_valid(), form_strong.errors)

        # 2. Login rate limiting
        cache.clear()

        # 4 consecutive bad attempts do not lock out yet
        for i in range(4):
            bad_attempt = self.client.post(reverse('login'), {
                'username': 'cust1',
                'password': f'wrongpass{i}'
            })
            self.assertEqual(bad_attempt.status_code, 200)
            self.assertContains(bad_attempt, "Invalid username or password.")

        # 5th bad attempt triggers rate limit lockout
        lockout_attempt = self.client.post(reverse('login'), {
            'username': 'cust1',
            'password': 'wrongpass5'
        })
        self.assertEqual(lockout_attempt.status_code, 200)
        self.assertContains(lockout_attempt, "Too many failed login attempts. Please try again later.")

        # 6th attempt with correct credentials while locked out is still blocked
        blocked_attempt = self.client.post(reverse('login'), {
            'username': 'cust1',
            'password': 'password123'
        })
        self.assertEqual(blocked_attempt.status_code, 200)
        self.assertContains(blocked_attempt, "Too many failed login attempts. Please try again later.")

        # Clearing cache resets lockout
        cache.clear()

        # Successful login works and clears failed attempts
        good_login = self.client.post(reverse('login'), {
            'username': 'cust1',
            'password': 'password123'
        })
        self.assertEqual(good_login.status_code, 302)

    def test_malformed_coordinates_and_filters_handling(self):
        req = RepairRequest.objects.create(
            customer=self.cust_profile1,
            service_category=self.cat_ac,
            device_name='AC For Coordinate Test',
            problem_description='Testing coordinates and filters',
            location='MG Road',
            city='Vijayawada',
            preferred_date=timezone.now().date(),
            urgency=RepairRequest.URGENCY_LOW,
            status=RepairRequest.STATUS_PENDING,
        )

        self.client.login(username='cust1', password='password123')
        base_url = reverse('customer_repair_matches', args=[req.id])

        # 1. Missing latitude/longitude (standard request)
        res_missing = self.client.get(base_url)
        self.assertEqual(res_missing.status_code, 200)

        # 2. Valid latitude/longitude
        res_valid = self.client.get(f"{base_url}?latitude=16.5033&longitude=80.6465")
        self.assertEqual(res_valid.status_code, 200)
        req.refresh_from_db()
        self.assertAlmostEqual(req.latitude, 16.5033)
        self.assertAlmostEqual(req.longitude, 80.6465)

        # 3. Non-numeric latitude does not cause HTTP 500
        res_bad_lat = self.client.get(f"{base_url}?latitude=abc&longitude=80.6465")
        self.assertEqual(res_bad_lat.status_code, 200)
        self.assertContains(res_bad_lat, "Invalid latitude format")

        # 4. Non-numeric longitude does not cause HTTP 500
        res_bad_lon = self.client.get(f"{base_url}?latitude=16.5033&longitude=xyz")
        self.assertEqual(res_bad_lon.status_code, 200)
        self.assertContains(res_bad_lon, "Invalid longitude format")

        # 5. Empty latitude does not cause HTTP 500
        res_empty_lat = self.client.get(f"{base_url}?latitude=&longitude=80.6465")
        self.assertEqual(res_empty_lat.status_code, 200)

        # 6. Empty longitude does not cause HTTP 500
        res_empty_lon = self.client.get(f"{base_url}?latitude=16.5033&longitude=")
        self.assertEqual(res_empty_lon.status_code, 200)

        # 7. Latitude outside [-90, 90] does not cause HTTP 500 and is rejected
        res_lat_out = self.client.get(f"{base_url}?latitude=95.5&longitude=80.6465")
        self.assertEqual(res_lat_out.status_code, 200)
        self.assertContains(res_lat_out, "Latitude must be between -90 and 90 degrees")

        # 8. Longitude outside [-180, 180] does not cause HTTP 500 and is rejected
        res_lon_out = self.client.get(f"{base_url}?latitude=16.5033&longitude=-185.0")
        self.assertEqual(res_lon_out.status_code, 200)
        self.assertContains(res_lon_out, "Longitude must be between -180 and 180 degrees")

        # 9. Non-numeric rating and max_cost do not cause HTTP 500
        res_bad_filters = self.client.get(f"{base_url}?rating=not-a-number&max_cost=invalid-cost")
        self.assertEqual(res_bad_filters.status_code, 200)

    def test_final_repair_cost_validation(self):
        req = RepairRequest.objects.create(
            customer=self.cust_profile1,
            service_category=self.cat_ac,
            device_name='AC Unit For Cost Validation',
            problem_description='Gas charging',
            location='MG Road',
            city='Vijayawada',
            preferred_date=timezone.now().date(),
            urgency=RepairRequest.URGENCY_MEDIUM,
            status=RepairRequest.STATUS_IN_PROGRESS,
            selected_technician=self.tech_profile1,
        )
        job = Job.objects.create(
            repair_request=req,
            technician=self.tech_profile1,
            customer=self.cust_profile1,
            status=Job.STATUS_IN_PROGRESS
        )

        self.client.login(username='tech1', password='password123')
        update_url = reverse('technician_update_job_status', args=[job.id])

        # 1. Missing final_cost rejected
        res_missing = self.client.post(update_url, {'status': Job.STATUS_COMPLETED, 'final_cost': ''})
        self.assertEqual(res_missing.status_code, 302)
        job.refresh_from_db()
        self.assertEqual(job.status, Job.STATUS_IN_PROGRESS)

        # 2. Non-numeric final_cost rejected
        res_nan = self.client.post(update_url, {'status': Job.STATUS_COMPLETED, 'final_cost': 'not-numeric'})
        self.assertEqual(res_nan.status_code, 302)
        job.refresh_from_db()
        self.assertEqual(job.status, Job.STATUS_IN_PROGRESS)

        # 3. Negative cost rejected
        res_neg = self.client.post(update_url, {'status': Job.STATUS_COMPLETED, 'final_cost': '-150.00'})
        self.assertEqual(res_neg.status_code, 302)
        job.refresh_from_db()
        self.assertEqual(job.status, Job.STATUS_IN_PROGRESS)

        # 4. Extremely large cost rejected
        res_huge = self.client.post(update_url, {'status': Job.STATUS_COMPLETED, 'final_cost': '5000000.00'})
        self.assertEqual(res_huge.status_code, 302)
        job.refresh_from_db()
        self.assertEqual(job.status, Job.STATUS_IN_PROGRESS)

        # 5. Zero cost accepted (e.g. warranty/free adjustment)
        res_zero = self.client.post(update_url, {'status': Job.STATUS_COMPLETED, 'final_cost': '0.00'})
        self.assertEqual(res_zero.status_code, 302)
        job.refresh_from_db()
        self.assertEqual(job.status, Job.STATUS_COMPLETED)
        self.assertEqual(job.final_cost, Decimal('0.00'))

        # 6. Valid positive final cost accepted on a new job
        req2 = RepairRequest.objects.create(
            customer=self.cust_profile1,
            service_category=self.cat_ac,
            device_name='AC Unit 2',
            problem_description='Filter clean',
            location='MG Road',
            city='Vijayawada',
            preferred_date=timezone.now().date(),
            urgency=RepairRequest.URGENCY_MEDIUM,
            status=RepairRequest.STATUS_IN_PROGRESS,
            selected_technician=self.tech_profile1,
        )
        job2 = Job.objects.create(
            repair_request=req2,
            technician=self.tech_profile1,
            customer=self.cust_profile1,
            status=Job.STATUS_IN_PROGRESS
        )
        update_url2 = reverse('technician_update_job_status', args=[job2.id])
        res_valid = self.client.post(update_url2, {'status': Job.STATUS_COMPLETED, 'final_cost': '750.00'})
        self.assertEqual(res_valid.status_code, 302)
        job2.refresh_from_db()
        self.assertEqual(job2.status, Job.STATUS_COMPLETED)
        self.assertEqual(job2.final_cost, Decimal('750.00'))

        # 7. Model clean() validation
        job2.final_cost = Decimal('-1.00')
        with self.assertRaises(ValidationError):
            job2.clean()

        job2.final_cost = Decimal('100001.00')
        with self.assertRaises(ValidationError):
            job2.clean()

        job2.final_cost = Decimal('500.00')
        job2.clean()  # should not raise

    def test_production_configuration_and_security_headers(self):
        # 1. Standard security headers emitted by responses
        res = self.client.get(reverse('home'))
        self.assertEqual(res.headers.get('X-Content-Type-Options'), 'nosniff')
        self.assertEqual(res.headers.get('X-Frame-Options'), 'DENY')
        self.assertEqual(res.headers.get('Referrer-Policy'), 'same-origin')

        # 2. Host header validation when DEBUG=False
        with override_settings(DEBUG=False, ALLOWED_HOSTS=['example.com', 'testserver']):
            client = Client()
            # Allowed host works
            good_res = client.get(reverse('home'), HTTP_HOST='example.com')
            self.assertEqual(good_res.status_code, 200)

            # Disallowed host returns 400 Bad Request
            bad_res = client.get(reverse('home'), HTTP_HOST='attacker.com')
            self.assertEqual(bad_res.status_code, 400)

        # 3. Verify security settings attributes exist on settings
        self.assertTrue(hasattr(settings, 'SESSION_COOKIE_SECURE'))
        self.assertTrue(hasattr(settings, 'CSRF_COOKIE_SECURE'))
        self.assertTrue(hasattr(settings, 'SECURE_SSL_REDIRECT'))
        self.assertTrue(hasattr(settings, 'SECURE_HSTS_SECONDS'))
        self.assertTrue(hasattr(settings, 'SECURE_HSTS_INCLUDE_SUBDOMAINS'))
        self.assertTrue(hasattr(settings, 'SECURE_HSTS_PRELOAD'))


