from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
from accounts.models import CustomerProfile
from services.models import ServiceCategory
from technicians.models import TechnicianProfile, TechnicianSkill
from repairs.models import RepairRequest, Job, JobStatusHistory, TechnicianMatch
from repairs.matching import haversine_distance, calculate_distance_score, calculate_cost_score, find_and_rank_technicians
from reviews.models import Review

User = get_user_model()


class RepairNowTestSuite(TestCase):
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

        self.admin_user = User.objects.create_superuser(username='admin_test', password='password123', role=User.ROLE_ADMIN)

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

        logout_res = self.client.get(reverse('logout'))
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
        accept_res = self.client.get(reverse('technician_accept_request', args=[req.id]))
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
