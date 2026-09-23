<div align="center">

# 🔧 RepairNow

**On-Demand Repair Technician Platform**

Connecting customers with verified local technicians — from request to repair to review.

![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)
![Django](https://img.shields.io/badge/Django-5.1-092E20?logo=django&logoColor=white)
![MySQL](https://img.shields.io/badge/MySQL-8.x-4479A1?logo=mysql&logoColor=white)
![License](https://img.shields.io/badge/License-Educational-lightgrey)

**Last Updated:** September 18, 2026

</div>

---

## 📖 Overview

**RepairNow** is a full-stack Django web application that connects customers who need repair services with verified local technicians. Customers submit repair requests, the platform's rule-based matching engine recommends the best-fit technicians, and the entire job lifecycle — from acceptance to completion and review — is managed in one place.

The platform supports three distinct roles (**Customer**, **Technician**, **Admin**), each with a dedicated portal and role-based access control.

---

## ✨ Features

### 👤 Customer Portal
- Register, log in, and manage profile
- Create repair requests with service category, problem description, location, urgency, preferred date/time, and optional budget
- Receive ranked technician recommendations with a visible match-score badge
- Compare technicians by rating, experience, estimated cost, and distance
- Select a technician and track job status in real time
- Submit star ratings and reviews after job completion
- View full service history and in-app notifications

### 🔧 Technician Portal
- Register (pending admin verification), log in, and manage profile
- Set a weekly availability schedule
- Receive and accept/reject incoming repair requests
- Manage active jobs with status progression controls:
  `On The Way → Arrived → In Progress → Completed`
- Enter the final cost at completion
- View received reviews, earnings history, and notifications
- Quick availability toggle (Online / Busy / Offline)

### 🛡️ Admin Portal
- Dashboard with platform KPIs (users, jobs, ratings, verifications, etc.)
- Verify / reject technician registrations
- Manage users, technicians, service categories, requests, reviews, and complaints
- Monitor full platform activity

---

## 🧰 Tech Stack

| Layer | Technology |
|-------|-----------|
| Language | Python 3.10+ |
| Framework | Django 5.1 |
| Database | MySQL 8.x |
| MySQL Driver | PyMySQL + cryptography |
| Image Handling | Pillow |
| Config | python-dotenv |
| Frontend | Custom CSS design system + Vanilla JS (Font Awesome icons) |

---

## 📦 Requirements

```
Django>=5.1.0
pymysql>=1.2.0
cryptography>=43.0.0
Pillow>=10.0.0
python-dotenv>=1.0.0
```

---

## 🚀 Installation & Setup

### 1. Prerequisites
- Python 3.10+
- MySQL 8.x running locally
- `pip` available

### 2. Clone the Repository
```bash
git clone https://github.com/mahender-reddy85/RepairNow.git
cd RepairNow
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Create the MySQL Database
```sql
CREATE DATABASE repairnow_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

### 5. Configure Environment Variables
Copy `.env.example` to `.env` and fill in your values:
```
SECRET_KEY=your-secret-key-here
DEBUG=True
USE_SQLITE=False
DB_NAME=repairnow_db
DB_USER=root
DB_PASSWORD=your_mysql_password
DB_HOST=127.0.0.1
DB_PORT=3306
GOOGLE_MAPS_API_KEY=
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

Visit **http://127.0.0.1:8000/**

---

## ⚙️ Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `SECRET_KEY` | Django secret key | *required* |
| `DEBUG` | Debug mode (`True`/`False`) | `True` |
| `USE_SQLITE` | Use SQLite instead of MySQL | `False` |
| `DB_NAME` | MySQL database name | `repairnow_db` |
| `DB_USER` | MySQL username | `root` |
| `DB_PASSWORD` | MySQL password | *required* |
| `DB_HOST` | MySQL host | `127.0.0.1` |
| `DB_PORT` | MySQL port | `3306` |
| `GOOGLE_MAPS_API_KEY` | Optional Google Maps key | *(empty)* |

> **Note:** When `USE_SQLITE=False` (default), `DB_NAME`, `DB_USER`, and `DB_PASSWORD` are required. Set `USE_SQLITE=True` to fall back to a local `db.sqlite3` file.

---

## 🔑 Default Credentials (after `seed_data`)

| Role | Username | Password |
|------|----------|----------|
| Admin | `repairnow` | `123456` |
| Customer | `ramesh_v` | `user1234` |
| Customer | `priya_s` | `user1234` |
| Customer | `ananya_p` | `user1234` |
| Customer | `vikram_r` | `user1234` |
| Technician | `suresh_tech` | `tech1234` |
| Technician | `naresh_ac` | `tech1234` |
| Technician | `rajesh_washer` | `tech1234` |
| Technician | `manoj_mobile` | `tech1234` |
| Technician | `arun_plumber` | `tech1234` |
| Technician | `pending_tech` | `tech1234` *(pending verification)* |

---

## 🗂️ Project Structure

```
RepairNow/
├── .env                          # Local environment config (not committed)
├── .env.example                  # Environment variable template
├── requirements.txt
├── manage.py
│
├── repairnow/                    # Project package
│   ├── settings.py               # Settings (MySQL / SQLite switch)
│   ├── urls.py                   # Master URL dispatcher
│   ├── admin_views.py            # Custom admin portal views
│   └── __init__.py               # PyMySQL install_as_MySQLdb()
│
├── accounts/                     # Authentication & user profiles
│   ├── models.py                 # User (AbstractUser), CustomerProfile
│   ├── forms.py                  # Login, registration, profile forms
│   ├── views.py                  # Login, logout, register, redirect
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
│   ├── tests.py                  # 16-test automated suite
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
    ├── base.html                 # Master layout (navbar, alerts)
    ├── home.html                 # Landing page
    ├── about.html
    ├── services.html
    ├── accounts/                 # login, register_customer, register_technician
    ├── customer/                 # dashboard, repair, matches, track, ...
    ├── technician/               # dashboard, profile, jobs, ...
    └── admin/                    # dashboard, users, technicians, ...
```

---

## 👥 User Roles

| Role | Access | How to Register |
|------|--------|-----------------|
| **Customer** | Create requests, track jobs, review technicians | `/register/customer/` |
| **Technician** | Receive & manage jobs, set availability | `/register/technician/` — requires admin verification |
| **Admin** | Full platform management | Created via `createsuperuser` or seed data |

---

## 🧠 Matching Algorithm

When a customer submits a repair request, the system scores every eligible technician using **5 weighted factors**:

| Factor | Normal Weight | Emergency Weight |
|--------|--------------|-----------------|
| Skill match | 35% | 25% |
| Availability | 20% | 30% |
| Distance | 20% | 25% |
| Rating | 15% | 12% |
| Cost compatibility | 10% | 8% |

**Rules:**
- Only `VERIFIED` + `is_active=True` technicians are considered
- Distance uses the **Haversine formula** when GPS coordinates are available; falls back to city comparison
- Emergency requests exclude `OFFLINE` technicians and those more than **35 km** away
- Skill score = `95 + min(years_experience, 5)` — maxes at 100 for 5+ year technicians
- Scores are stored in `TechnicianMatch` and displayed as a percentage badge on the matches page

---

## 🔗 URL Reference

| URL | Description |
|-----|-------------|
| `/` | Landing page |
| `/about/` | About page |
| `/services/` | Services list |
| `/login/` | Login |
| `/logout/` | Logout |
| `/register/customer/` | Customer registration |
| `/register/technician/` | Technician registration |
| `/customer/dashboard/` | Customer home |
| `/customer/repair/create/` | Create a new repair request |
| `/customer/repair/<id>/matches/` | View matched technicians |
| `/customer/repair/<id>/track/` | Live job tracking |
| `/technician/dashboard/` | Technician home |
| `/technician/jobs/<id>/` | Job workspace |
| `/admin/` | Custom admin portal |
| `/django-admin/` | Django built-in admin |

---

## 🧪 Running Tests

```bash
python manage.py test repairs
```

Expected result: **16/16 tests pass**

The test suite covers:
- User registration and authentication
- Role-based access control
- Repair request creation and auto-matching
- Form validation (past-date, budget)
- Matching engine correctness (Haversine, cost scoring)
- Full job lifecycle (accept → on_way → arrived → in_progress → complete)
- Review validation, average rating recalculation, duplicate prevention
- Notification deletion and template integrity

---

## 📄 License

This project was built as a student portfolio project and is provided for **educational purposes**.