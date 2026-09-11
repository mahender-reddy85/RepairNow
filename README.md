# RepairNow 🔧

**On-Demand Repair Technician Platform**

RepairNow connects customers who need repair services with verified local technicians. Customers submit repair requests, the platform's matching engine recommends the best-fit technicians, and the entire job lifecycle (from acceptance to completion and review) is managed in one place.

---

## Features

### Customer Portal
- Register, log in, manage profile
- Create repair requests with: service category, problem description, photo upload, location, urgency, preferred date/time, and optional budget
- Receive ranked technician recommendations (matching score shown)
- Compare technicians by rating, experience, rate, distance
- Select a technician and track job status in real time
- Submit reviews and star ratings after job completion
- View full service history and notifications

### Technician Portal
- Register (pending admin verification), log in, manage profile
- Set weekly availability schedule
- Receive and accept/reject incoming repair requests
- Manage active jobs with status progression controls:
  - `On The Way -> Arrived -> In Progress -> Completed`
- Enter final cost at completion
- View received reviews, earnings history, notifications
- Quick availability toggle (Online / Busy / Offline)

### Admin Portal
- Dashboard with 8 KPIs (users, jobs, revenue, ratings, etc.)
- Verify / reject technician registrations
- Manage users, technicians, service categories, requests, reviews, complaints
- View full platform activity

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Language | Python 3.13 |
| Framework | Django 5.x |
| Database | MySQL 8.4 |
| Image handling | Pillow |
| MySQL driver | PyMySQL + cryptography |
| Config | python-dotenv |
| Frontend | Bootstrap 5, Vanilla JS |

---

## Requirements

```
Django>=4.2
PyMySQL>=1.0
cryptography>=3.4
Pillow>=9.0
python-dotenv>=0.19
```

---

## Installation & Setup

### 1. Prerequisites

- Python 3.10+
- MySQL 8.x running locally
- pip available

### 2. Clone / Download the Project

```bash
git clone <repo-url> RepairNow
cd RepairNow
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Create the MySQL Database

Open MySQL shell and run:

```sql
CREATE DATABASE repairnow_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

### 5. Configure Environment Variables

Copy `.env.example` to `.env` and fill in your values:

```
SECRET_KEY=your-secret-key-here
DEBUG=True
DB_NAME=repairnow_db
DB_USER=root
DB_PASSWORD=your_mysql_password
DB_HOST=127.0.0.1
DB_PORT=3306
```

### 6. Apply Migrations

```bash
python manage.py makemigrations
python manage.py migrate
```

### 7. Seed Demo Data

```bash
python manage.py seed_data
```

### 8. Run the Development Server

```bash
python manage.py runserver
```

Visit http://127.0.0.1:8000/

---

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `SECRET_KEY` | Django secret key | *required* |
| `DEBUG` | Debug mode (True/False) | `True` |
| `DB_NAME` | MySQL database name | `repairnow_db` |
| `DB_USER` | MySQL username | `root` |
| `DB_PASSWORD` | MySQL password | *required* |
| `DB_HOST` | MySQL host | `127.0.0.1` |
| `DB_PORT` | MySQL port | `3306` |

---

## Default Credentials (after seed_data)

| Role | Username | Password |
|------|----------|----------|
| Admin | `admin` | `admin123` |
| Customer | `ramesh_v` | `password123` |
| Customer | `priya_s` | `password123` |
| Customer | `ananya_p` | `password123` |
| Customer | `vikram_r` | `password123` |
| Customer | `sneha_r` | `password123` |
| Technician | `ravi_kumar` | `password123` |
| Technician | `arjun_reddy` | `password123` |
| Technician | `suresh_kumar` | `password123` |
| Technician | `rajesh_varma` | `password123` |
| Technician | `manoj_singh` | `password123` |
| Technician | `kiran_rao` | `password123` |

---

## Project Structure

```
RepairNow/
├── .env                          # Local environment config (not committed)
├── .env.example                  # Environment variable template
├── requirements.txt
├── manage.py
│
├── repairnow/                    # Project package
│   ├── settings.py
│   ├── urls.py                   # Master URL dispatcher
│   ├── views.py                  # Custom error handlers (404, 403, 500)
│   ├── admin_views.py            # Custom admin portal views
│   └── __init__.py               # PyMySQL install
│
├── accounts/                     # Authentication & user profiles
│   ├── models.py                 # User (AbstractUser), CustomerProfile
│   ├── forms.py                  # Login, registration, profile forms
│   ├── views.py                  # Login, logout, register
│   ├── decorators.py             # @customer_required, @technician_required, @admin_required
│   └── urls.py
│
├── services/                     # Service categories
│   ├── models.py                 # ServiceCategory (slug auto-gen)
│   ├── views.py                  # Home, about, services list
│   └── urls.py
│
├── technicians/                  # Technician profiles & availability
│   ├── models.py                 # TechnicianProfile, TechnicianSkill, Availability
│   ├── views.py                  # Full technician portal views
│   └── urls.py
│
├── repairs/                      # Core repair request lifecycle
│   ├── models.py                 # RepairRequest, TechnicianMatch, Job, JobStatusHistory
│   ├── matching.py               # 5-factor rule-based matching engine
│   ├── forms.py                  # RepairRequestForm
│   ├── views.py                  # Customer repair lifecycle views
│   ├── urls.py
│   ├── tests.py                  # 13-test automated suite
│   └── management/commands/
│       └── seed_data.py          # Demo data seeder
│
├── reviews/                      # Reviews & complaints
│   ├── models.py                 # Review (OneToOne with Job), Complaint
│   ├── forms.py
│   ├── views.py
│   └── urls.py
│
├── notifications/                # In-app notifications
│   ├── models.py                 # Notification + send_notification() helper
│   ├── views.py
│   ├── context_processors.py     # Injects unread count into all templates
│   └── urls.py
│
├── static/
│   ├── css/style.css             # Full responsive design system
│   └── js/main.js                # Vanilla JS interactions & AJAX
│
└── templates/
    ├── base.html                 # Master layout (navbar, alerts, footer)
    ├── home.html                 # Landing page
    ├── about.html
    ├── services.html
    ├── accounts/                 # login, register_customer, register_technician
    ├── customer/                 # dashboard, repair_create, matches, track, ...
    ├── technician/               # dashboard, profile, availability, jobs, ...
    └── admin/                    # dashboard, users, technicians, ...
```

---

## User Roles

| Role | Access | How to register |
|------|--------|-----------------|
| **Customer** | Create requests, track jobs, review technicians | /accounts/register/customer/ |
| **Technician** | Receive & manage jobs, set availability | /accounts/register/technician/ — requires admin verification |
| **Admin** | Full platform management | Created via createsuperuser or seed data |

---

## Matching Algorithm

When a customer submits a repair request, the system scores every eligible technician using 5 weighted factors:

| Factor | Normal weight | Emergency weight |
|--------|--------------|-----------------|
| Skill match | 35% | 25% |
| Availability | 20% | 30% |
| Distance | 20% | 25% |
| Rating | 15% | 10% |
| Cost compatibility | 10% | 10% |

**Rules:**
- Only VERIFIED + is_active=True technicians are considered
- Distance uses Haversine formula when GPS coordinates are available; falls back to city comparison
- Emergency requests exclude OFFLINE technicians and those > 35 km away
- Skill score = 95 + min(years_experience, 5) — maxes at 100 for 5+ year techs
- Scores are stored in TechnicianMatch and displayed as a percentage badge on the matches page

---

## URL Reference

| URL | Description |
|-----|-------------|
| / | Landing page |
| /accounts/login/ | Login |
| /accounts/register/customer/ | Customer registration |
| /accounts/register/technician/ | Technician registration |
| /customer/dashboard/ | Customer home |
| /customer/repair/create/ | Create a new repair request |
| /customer/repair/<id>/matches/ | View matched technicians |
| /customer/repair/<id>/track/ | Live job tracking |
| /technician/dashboard/ | Technician home |
| /technician/jobs/<id>/ | Job workspace |
| /admin/dashboard/ | Custom admin portal |
| /django-admin/ | Django built-in admin |

---

## Running Tests

```bash
python manage.py test repairs
```

Expected result: **13/13 tests pass**

The test suite covers:
- User registration and authentication
- Role-based access control
- Repair request creation and auto-matching
- Form validation (past-date, budget)
- Matching engine correctness (Haversine, cost scoring)
- Full job lifecycle (accept -> on_way -> arrived -> in_progress -> complete)
- Review validation, average rating recalculation, duplicate prevention

---

## License

This project was built as a student portfolio project. It is provided for educational purposes.
