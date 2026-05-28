<![CDATA[<div align="center">

# 🏥 ProClinic

**Intelligent Clinic Management System**

[![Python 3.12](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Django 6.0](https://img.shields.io/badge/Django-6.0-092E20?logo=django&logoColor=white)](https://www.djangoproject.com/)
[![DRF 3.16](https://img.shields.io/badge/DRF-3.16-ff1709?logo=django&logoColor=white)](https://www.django-rest-framework.org/)
[![PostgreSQL 16](https://img.shields.io/badge/PostgreSQL-16-4169E1?logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?logo=docker&logoColor=white)](https://www.docker.com/)
[![Render](https://img.shields.io/badge/Deploy-Render-46E3B7?logo=render&logoColor=white)](https://render.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

A full-stack, role-based clinic management platform built with Django 6.0 and Django REST Framework. ProClinic digitizes the complete clinical workflow — from patient registration and appointment scheduling through prescription generation, billing, lab report management, and research publication review — with six distinct user roles, PDF export, Cloudinary media storage, AI-powered health assistant, automated audit logging, and production-ready deployment on Render.

[Live Demo](https://proclinic-lx2u.onrender.com) · [API Docs](#api-overview) · [Architecture](#system-architecture) · [Getting Started](#installation-guide)

</div>

---

## Table of Contents

- [Executive Summary](#executive-summary)
- [Key Features](#key-features)
- [Technology Stack](#technology-stack)
- [System Architecture](#system-architecture)
- [Project Structure](#project-structure)
- [Prerequisites](#prerequisites)
- [Installation Guide](#installation-guide)
- [Environment Configuration](#environment-configuration)
- [Database Setup](#database-setup)
- [Running the Application](#running-the-application)
- [Development Workflow](#development-workflow)
- [Testing](#testing)
- [API Overview](#api-overview)
- [Authentication & Authorization](#authentication--authorization)
- [Configuration Reference](#configuration-reference)
- [Deployment](#deployment)
- [Security Considerations](#security-considerations)
- [Monitoring & Logging](#monitoring--logging)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)
- [License](#license)

---

## Executive Summary

ProClinic is a comprehensive, production-grade clinic management system designed to serve multi-role medical facilities. It implements a monolithic Django architecture with a server-rendered frontend (Django templates) and a parallel RESTful JSON API (Django REST Framework + JWT), enabling both traditional web sessions and programmatic access.

The system supports **six user roles** — Administrator, Doctor, Receptionist, Pharmacist, Accountant, and Patient — each with a dedicated dashboard, granular permissions, and role-specific workflows. Key clinical workflows (appointment completion → draft invoice generation, prescription → pharmacy dispensing) are automated via Django signals, and every data mutation is captured by a comprehensive audit logging subsystem.

---

## Key Features

### 👤 Multi-Role Access Control
- **6 distinct roles**: Admin, Doctor, Receptionist, Pharmacist, Accountant, Patient
- Role-based login portals (Staff vs. Patient) with separate authentication flows
- Custom permission classes enforcing API-level and view-level access control
- OTP-based password recovery for patients via email (Gmail SMTP)

### 📅 Appointment Management
- Patient self-service booking with real-time doctor availability checks
- Double-booking prevention (doctor-level and patient-level conflict detection)
- Doctor unavailability block scheduling
- Receptionist appointment management: cancel, reschedule, check-in, mark no-show
- Status lifecycle: `SCHEDULED` → `CHECKED_IN` → `COMPLETED` → `CANCELLED` / `NOSHOW` / `RESCHEDULED`

### 📋 Electronic Health Records (EHR)
- Patient profiles with demographics, blood group, allergies, and contact information
- Visit records linked to appointments with diagnosis and clinical notes
- Lab report management with PDF upload (Cloudinary), verification, and archival workflow
- Patient self-service portal: view visits, prescriptions, invoices, and lab reports

### 💊 Prescription Management
- Doctor-created prescriptions linked to clinical visits
- Multi-item prescriptions with medicine name, dosage, instructions, and duration
- PDF export via WeasyPrint with A4 print-ready templates
- Pharmacist dispensing workflow with status tracking (`PENDING` → `DISPENSED`)

### 💰 Billing & Invoicing
- Automated draft invoice generation on appointment completion (via Django signals)
- Line-item support: Consultation, Medicine, Lab/Test, Procedure, Other
- Financial breakdown: subtotal, tax (GST), discount, grand total, paid/due amounts
- Medicine master catalog with default pricing
- Invoice lifecycle: `DRAFT` → `UNPAID` → `PARTIAL` → `PAID` → `REFUNDED`
- PDF invoice generation and email delivery

### 📄 Research Publications
- Doctors submit research papers with PDF uploads
- Admin approval/rejection workflow with reviewer notes
- Public listing of approved publications (no authentication required)
- Patient-facing publications portal

### 🤖 AI Health Assistant
- Google Gemini-powered conversational health assistant for patients
- Contextual responses based on patient medical history

### 📊 Audit & Compliance
- Automatic audit logging via Django signals (`pre_save`, `post_save`, `post_delete`)
- Tracks 6 entity types: Patient, Appointment, Prescription, Invoice, Publication, LabReport
- Records actor, action type (CREATE/UPDATE/DELETE), before/after diffs in JSON
- Sensitive fields (passwords, tokens) are automatically excluded from logs
- Admin-accessible audit log viewer with filtering and search

### 📄 PDF Generation
- WeasyPrint-based server-side PDF rendering for prescriptions and invoices
- A4 print-ready templates with clinic branding
- Cloudinary storage for generated PDFs in production

---

## Technology Stack

### Backend

| Technology | Version | Purpose |
|---|---|---|
| Python | 3.12 | Runtime |
| Django | 6.0.1 | Web framework |
| Django REST Framework | 3.16.1 | REST API layer |
| SimpleJWT | 5.5.1 | JWT authentication for API |
| django-filter | 25.2 | Queryset filtering for API and views |
| django-environ | 0.12.0 | Environment variable management |
| django-cors-headers | 4.9.0 | Cross-Origin Resource Sharing |
| psycopg2-binary | 2.9.11 | PostgreSQL adapter |
| Gunicorn | 25.3.0 | Production WSGI server |
| WhiteNoise | 6.12.0 | Static file serving in production |
| WeasyPrint | 68.1 | HTML → PDF generation |
| Pillow | 12.2.0 | Image processing |
| Cloudinary | 1.44.0 | Cloud media storage |
| django-cloudinary-storage | 0.3.0 | Django ↔ Cloudinary integration |
| Argon2-cffi | 25.1.0 | Password hashing (primary hasher) |
| google-generativeai | 0.8.3 | AI health assistant (Gemini API) |

### Frontend

| Technology | Purpose |
|---|---|
| Django Templates | Server-side HTML rendering |
| Custom CSS Design System | Component-based styling (`design-system.css`) |
| Vanilla JavaScript | Client-side interactivity, AJAX calls |
| SVG Icons | Custom icon set for UI components |

### Infrastructure

| Technology | Purpose |
|---|---|
| PostgreSQL 16 | Production database |
| SQLite | Local development database (fallback) |
| Redis 7 | Cache / message broker (Docker Compose) |
| Docker | Containerization |
| Render | Cloud hosting (free tier) |
| Cloudinary | Media file storage (PDFs, images) |

---

## System Architecture

```mermaid
graph TB
    subgraph Client["Client Layer"]
        Browser["Web Browser"]
        APIClient["API Client / Mobile App"]
    end

    subgraph Server["Django Application"]
        direction TB
        subgraph Middleware["Middleware Stack"]
            Security["SecurityMiddleware"]
            WhiteNoise["WhiteNoise"]
            Session["SessionMiddleware"]
            CORS["CorsMiddleware"]
            CSRF["CsrfMiddleware"]
            Auth["AuthenticationMiddleware"]
            Audit["AuditUserMiddleware"]
        end

        subgraph Auth_Layer["Authentication"]
            SessionAuth["Session Auth (Web)"]
            JWTAuth["JWT Auth (API)"]
        end

        subgraph Apps["Application Modules"]
            Accounts["accounts"]
            Patients["patients"]
            Appointments["appointments"]
            Prescriptions["prescriptions"]
            Billing["billing"]
            Publications["publications"]
            AuditApp["audit"]
            API["api"]
        end

        subgraph Templates_Layer["Frontend"]
            Templates["Django Templates"]
            Static["Static Assets"]
        end
    end

    subgraph External["External Services"]
        PostgreSQL["PostgreSQL 16"]
        Cloudinary_Svc["Cloudinary CDN"]
        Gmail["Gmail SMTP"]
        Gemini["Google Gemini AI"]
    end

    Browser -->|"Session Cookie"| SessionAuth
    APIClient -->|"Bearer JWT"| JWTAuth
    Auth_Layer --> Apps
    Apps --> PostgreSQL
    Apps -->|"Media Uploads"| Cloudinary_Svc
    Apps -->|"Email"| Gmail
    Apps -->|"AI Queries"| Gemini
    Apps --> Templates_Layer
```

### Data Flow: Appointment → Invoice (Signal-Driven)

```mermaid
sequenceDiagram
    participant D as Doctor
    participant App as Appointment Model
    participant Sig as billing.signals
    participant Inv as Invoice Model
    participant Med as MedicineMaster

    D->>App: Mark appointment COMPLETED
    App->>App: post_save signal fires
    App->>Sig: create_draft_invoice_on_completion()
    Sig->>Inv: Create DRAFT Invoice
    Sig->>Inv: Add CONSULTATION line item
    Sig->>Med: Lookup medicine prices
    Sig->>Inv: Add MEDICINE line items from prescription
    Sig->>Inv: recalculate_totals()
    Note over Inv: Invoice ready for Accountant review
```

### Audit Logging Pipeline

```mermaid
flowchart LR
    A["Model Save/Delete"] --> B["Django Signal"]
    B --> C{"Is Tracked Model?"}
    C -->|Yes| D["Capture old state (pre_save)"]
    D --> E["Compute diff (post_save)"]
    E --> F["Write AuditLog entry"]
    C -->|No| G["Skip"]
    F --> H["AuditLog Table"]
    H --> I["Admin Viewer / API"]
```

---

## Project Structure

```
ProClinic/
├── backend/                    # Django project root
│   ├── manage.py               # Django management entry point
│   ├── create_admin.py         # Auto-creates admin superuser on deploy
│   ├── .env                    # Local environment variables (not committed)
│   │
│   ├── core/                   # Django project settings & config
│   │   ├── settings.py         # Main settings (DB, auth, middleware, REST, etc.)
│   │   ├── urls.py             # Root URL configuration
│   │   ├── views.py            # Home, dashboard, design-system views
│   │   ├── wsgi.py             # WSGI entry point
│   │   ├── asgi.py             # ASGI entry point
│   │   └── utils.py            # Email notification helpers
│   │
│   ├── accounts/               # Authentication & user management
│   │   ├── models.py           # CustomUser (6 roles), PatientOTP
│   │   ├── views.py            # Login, signup, profile, staff CRUD, OTP password reset
│   │   ├── forms.py            # PatientSignUpForm, StaffCreationForm, ProfileForms
│   │   ├── urls.py             # Auth routes (/accounts/*)
│   │   └── admin.py            # CustomUserAdmin
│   │
│   ├── patients/               # Patient records & EHR
│   │   ├── models.py           # Patient, Visit, LabReport
│   │   ├── views.py            # Patient CRUD, lab reports, AI assistant
│   │   ├── serializers.py      # PatientSerializer (DRF)
│   │   ├── urls.py             # Patient routes (/patients/*)
│   │   └── utils.py            # Patient profile helpers
│   │
│   ├── appointments/           # Scheduling & availability
│   │   ├── models.py           # Appointment, DoctorUnavailability
│   │   ├── views.py            # Booking, doctor/receptionist views, slot API
│   │   ├── forms.py            # AppointmentForm, UnavailabilityForm, VisitNoteForm
│   │   └── urls.py             # Appointment routes (/appointments/*)
│   │
│   ├── prescriptions/          # Medication management
│   │   ├── models.py           # Prescription, PrescriptionItem
│   │   ├── views.py            # Create, pharmacist list/detail, dispense
│   │   ├── utils.py            # PDF generation (WeasyPrint)
│   │   └── urls.py             # Prescription routes (/prescriptions/*)
│   │
│   ├── billing/                # Financial management
│   │   ├── models.py           # Invoice, InvoiceItem, MedicineMaster
│   │   ├── views.py            # Invoice CRUD, medicine catalog, PDF download
│   │   ├── signals.py          # Auto-create draft invoice on appointment completion
│   │   ├── utils.py            # Invoice PDF generation, financial calculations
│   │   └── urls.py             # Billing routes (/billing/*)
│   │
│   ├── publications/           # Research paper management
│   │   ├── models.py           # Publication (with approval workflow)
│   │   ├── views.py            # Submit, approve/reject, public listing
│   │   ├── forms.py            # PublicationForm
│   │   └── urls.py             # Publication routes (/publications/*)
│   │
│   ├── audit/                  # Audit trail subsystem
│   │   ├── models.py           # AuditLog
│   │   ├── signals.py          # Automatic create/update/delete logging
│   │   ├── middleware.py       # AuditUserMiddleware (thread-local user capture)
│   │   ├── views.py            # Audit log viewer
│   │   └── urls.py             # Audit routes (/audit/*)
│   │
│   ├── api/                    # REST API layer
│   │   ├── views.py            # Staff-facing ViewSets (Appointment, Prescription, Invoice, etc.)
│   │   ├── patient_views.py    # Patient-facing API views
│   │   ├── serializers.py      # Staff API serializers
│   │   ├── patient_serializers.py  # Patient API serializers
│   │   ├── permissions.py      # IsPatient, IsDoctor, IsAdminRole, IsStaff
│   │   ├── filters.py          # DjangoFilterBackend filter classes
│   │   ├── pagination.py       # StandardResultsSetPagination, LargeResultsSetPagination
│   │   ├── urls.py             # API router + JWT endpoints
│   │   ├── patient_urls.py     # Patient API endpoints (/api/patient/*)
│   │   ├── tests.py            # Patient API test suite (55+ test cases)
│   │   └── tests_extended.py   # Staff API, audit, publication, model tests (60+ test cases)
│   │
│   └── media/                  # Local media uploads (dev only)
│
├── frontend/                   # Frontend assets (served by Django)
│   ├── templates/              # Django HTML templates
│   │   ├── base.html           # Base layout template
│   │   ├── dashboard.html      # Role-based dashboard router
│   │   ├── dashboards/         # Role-specific dashboards (6 files)
│   │   │   ├── admin.html
│   │   │   ├── doctor.html
│   │   │   ├── patient.html
│   │   │   ├── receptionist.html
│   │   │   ├── pharmacist.html
│   │   │   └── accountant.html
│   │   ├── accounts/           # Login, signup, profile templates
│   │   ├── appointments/       # Booking & management templates
│   │   ├── patients/           # Patient list, detail, EHR templates
│   │   ├── prescriptions/      # Prescription create & pharmacy templates
│   │   ├── billing/            # Invoice & medicine catalog templates
│   │   ├── publications/       # Research paper templates
│   │   ├── audit/              # Audit log viewer templates
│   │   ├── components/         # Reusable UI components
│   │   ├── layouts/            # Page layout templates
│   │   ├── prototype/          # A4 print prototypes (prescription, invoice)
│   │   └── registration/       # Auth flow templates
│   │
│   ├── static/proclinic/       # Static assets
│   │   ├── design-system.css   # Complete CSS design system
│   │   ├── js/                 # JavaScript modules
│   │   └── icons/              # SVG icon set
│   │
│   └── media/                  # Media uploads (Docker volume mount point)
│
├── docs/                       # Project documentation
│   ├── api.md                  # API endpoint reference
│   ├── architecture.md         # Architecture documentation
│   ├── models.md               # Data model documentation
│   ├── workflow.md             # Business workflow documentation
│   └── proclinic_design_handoff.md  # UI/UX design specifications
│
├── deliverables/               # UI mockups and prototypes
│   └── png/                    # 15 UI mockup images (desktop, tablet, mobile)
│
├── docker-compose.yml          # Multi-service dev environment (PostgreSQL + Redis + Web)
├── Dockerfile                  # Production container (Python 3.12-slim + Gunicorn)
├── render.yaml                 # Render Blueprint (auto-deploy configuration)
├── build.sh                    # Render build script
├── requirements.txt            # Python dependencies
└── .gitignore                  # Git exclusions
```

---

## Prerequisites

| Requirement | Version | Notes |
|---|---|---|
| Python | ≥ 3.12 | Required for Django 6.0 |
| pip | Latest | Python package manager |
| Git | Any | Version control |
| PostgreSQL | ≥ 16 | Production database (optional for local dev — SQLite fallback) |
| Docker & Docker Compose | Latest | Optional: containerized development |
| WeasyPrint system dependencies | — | Required for PDF generation (see below) |

### WeasyPrint System Dependencies

WeasyPrint requires system-level libraries for PDF rendering. Install them before `pip install`:

**Ubuntu / Debian:**
```bash
sudo apt-get install -y \
    libpango-1.0-0 libpangoft2-1.0-0 libharfbuzz0b \
    libfontconfig1 libgdk-pixbuf-2.0-0 libcairo2 \
    shared-mime-info libjpeg62-turbo-dev zlib1g-dev
```

**macOS (Homebrew):**
```bash
brew install pango cairo gdk-pixbuf libffi
```

**Windows:**
Follow the [WeasyPrint Windows installation guide](https://doc.courtbouillon.org/weasyprint/stable/first_steps.html#windows).

---

## Installation Guide

### Option A: Local Development (Recommended for development)

```bash
# 1. Clone the repository
git clone https://github.com/24Chessman/ProClinic.git
cd ProClinic

# 2. Create and activate a virtual environment
python -m venv venv
source venv/bin/activate        # Linux/macOS
# venv\Scripts\activate         # Windows

# 3. Install Python dependencies
pip install --upgrade pip
pip install -r requirements.txt

# 4. Configure environment variables
cp backend/.env.example backend/.env   # Or create manually (see below)

# 5. Apply database migrations
cd backend
python manage.py migrate

# 6. Create an admin superuser
python create_admin.py
# Creates: username=admin, password=Admin@12345, role=ADMIN

# 7. Run the development server
python manage.py runserver
```

The application will be available at **http://127.0.0.1:8000**

### Option B: Docker Compose (Full stack)

```bash
# 1. Clone the repository
git clone https://github.com/24Chessman/ProClinic.git
cd ProClinic

# 2. Start all services (PostgreSQL + Redis + Django)
docker compose up --build

# 3. Apply migrations (in a separate terminal)
docker compose exec web python backend/manage.py migrate

# 4. Create admin user
docker compose exec web python backend/create_admin.py
```

Services will be available at:
- **Django App**: http://localhost:8000
- **PostgreSQL**: localhost:5432
- **Redis**: localhost:6379

---

## Environment Configuration

Create `backend/.env` with the following variables:

```env
# ── Django Core ──────────────────────────────────────────────
DEBUG=True
SECRET_KEY=your-secret-key-here
ALLOWED_HOSTS=127.0.0.1,localhost

# ── Database ─────────────────────────────────────────────────
# Leave unset for SQLite (local dev); set for PostgreSQL:
# DATABASE_URL=postgres://user:password@host:5432/dbname

# ── Clinic Configuration ─────────────────────────────────────
CONSULTATION_FEE=500.00
GST_RATE=0.18

# ── Cloudinary (Production media storage) ────────────────────
# CLOUDINARY_CLOUD_NAME=your-cloud-name
# CLOUDINARY_API_KEY=your-api-key
# CLOUDINARY_API_SECRET=your-api-secret

# ── Email (Gmail SMTP for OTP & invoice delivery) ────────────
# GMAIL_USER=your-email@gmail.com
# GMAIL_PASS=your-app-password

# ── Google Gemini AI (Patient health assistant) ──────────────
# GEMINI_API_KEY=your-gemini-api-key

# ── Security (Production only) ───────────────────────────────
# SECURE_SSL_REDIRECT=True
# SESSION_COOKIE_SECURE=True
# CSRF_COOKIE_SECURE=True
# SECURE_HSTS_SECONDS=31536000
# SECURE_HSTS_INCLUDE_SUBDOMAINS=True
# SECURE_HSTS_PRELOAD=True
# CSRF_TRUSTED_ORIGINS=https://your-domain.com
```

### Environment Variable Reference

| Variable | Required | Default | Description |
|---|---|---|---|
| `DEBUG` | No | `False` | Enable Django debug mode |
| `SECRET_KEY` | **Yes** | — | Django secret key for cryptographic signing |
| `ALLOWED_HOSTS` | **Yes** | — | Comma-separated list of allowed hostnames |
| `DATABASE_URL` | No | SQLite | PostgreSQL connection string |
| `CONSULTATION_FEE` | No | `500.00` | Default consultation fee (INR) |
| `GST_RATE` | No | `0.18` | GST tax rate (18%) |
| `CLOUDINARY_CLOUD_NAME` | No | — | Cloudinary cloud name for media storage |
| `CLOUDINARY_API_KEY` | No | — | Cloudinary API key |
| `CLOUDINARY_API_SECRET` | No | — | Cloudinary API secret |
| `GMAIL_USER` | No | — | Gmail address for sending emails |
| `GMAIL_PASS` | No | — | Gmail app password |
| `RENDER` | No | — | Set to `true` when deploying on Render |
| `SECURE_SSL_REDIRECT` | No | `False` | Force HTTPS redirects |
| `SESSION_COOKIE_SECURE` | No | `False` | Secure flag on session cookies |
| `CSRF_COOKIE_SECURE` | No | `False` | Secure flag on CSRF cookies |
| `SECURE_HSTS_SECONDS` | No | `0` | HSTS max-age in seconds |
| `CSRF_TRUSTED_ORIGINS` | No | `[]` | Trusted origins for CSRF validation |

---

## Database Setup

### Local Development (SQLite — Zero Config)

When `DATABASE_URL` is not set, Django automatically uses SQLite:

```bash
cd backend
python manage.py migrate
```

### PostgreSQL (Production / Docker)

```bash
# Create the database
createdb proclinic

# Set the connection string in backend/.env
DATABASE_URL=postgres://proclinic_user:proclinic_pass@localhost:5432/proclinic

# Run migrations
cd backend
python manage.py migrate
```

### Data Model Overview

```mermaid
erDiagram
    CustomUser ||--o| Patient : "user (1:1)"
    CustomUser ||--o{ PatientOTP : "otps"
    CustomUser ||--o{ Appointment : "doctor_appointments"
    CustomUser ||--o{ Prescription : "prescriptions_written"
    CustomUser ||--o{ Publication : "publications"
    CustomUser ||--o{ AuditLog : "audit_logs"

    Patient ||--o{ Appointment : "appointments"
    Patient ||--o{ Visit : "visits"
    Patient ||--o{ Prescription : "prescriptions"
    Patient ||--o{ Invoice : "invoices"
    Patient ||--o{ LabReport : "lab_reports"

    Appointment ||--o| Visit : "visit (1:1)"
    Appointment ||--o| Invoice : "invoice (1:1)"

    Visit ||--o{ Prescription : "prescriptions"
    Prescription ||--o{ PrescriptionItem : "items"

    Invoice ||--o{ InvoiceItem : "items"

    CustomUser {
        string role "ADMIN|DOCTOR|RECEPTIONIST|PHARMACIST|ACCOUNTANT|PATIENT"
        string phone_number
        string specialization
    }

    Patient {
        string first_name
        string last_name
        date date_of_birth
        string gender
        string blood_group
        string contact_number
        string email
        text address
        text allergies
    }

    Appointment {
        datetime scheduled_time
        text reason
        string status "SCHEDULED|CHECKED_IN|COMPLETED|CANCELLED|NOSHOW|RESCHEDULED"
        string room_assignment
    }

    Visit {
        datetime visit_date
        text notes
        text diagnosis
    }

    Prescription {
        string dispense_status "PENDING|DISPENSED"
        datetime dispensed_at
    }

    PrescriptionItem {
        string medicine_name
        string dosage
        string instructions
        string duration
    }

    Invoice {
        string status "DRAFT|UNPAID|PARTIAL|PAID|REFUNDED"
        decimal subtotal
        decimal tax_amount
        decimal discount_amount
        decimal grand_total
    }

    InvoiceItem {
        string item_type "CONSULTATION|MEDICINE|LAB|PROCEDURE|OTHER"
        string service_name
        decimal unit_cost
        int quantity
    }

    LabReport {
        string test_name
        date report_date
        string status "pending|verified|archived"
    }

    Publication {
        string title
        text abstract
        string authors
        string status "DRAFT|PENDING|APPROVED|REJECTED"
    }

    AuditLog {
        string action_type "CREATE|UPDATE|DELETE|LOGIN"
        string entity_type
        int entity_id
        json changes
    }
```

---

## Running the Application

### Development Server

```bash
cd backend
python manage.py runserver
```

### With Docker Compose

```bash
docker compose up
```

### Default Login Credentials

After running `create_admin.py`:

| Role | Username | Password |
|---|---|---|
| Administrator | `admin` | `Admin@12345` |

Additional staff accounts can be created through the Admin dashboard (`/accounts/staff/create/`). Patient accounts are created via self-registration at `/accounts/signup/patient/`.

### Role-Based Dashboards

After login, users are automatically redirected to their role-specific dashboard:

| Role | Dashboard | Key Functions |
|---|---|---|
| **Admin** | `/dashboard/` | Staff management, audit logs, publication review, system overview |
| **Doctor** | `/dashboard/` | Today's appointments, patient visits, prescriptions, research papers |
| **Receptionist** | `/dashboard/` | Appointment booking/management, patient registration, check-in |
| **Pharmacist** | `/dashboard/` | Pending prescriptions, dispense tracking |
| **Accountant** | `/dashboard/` | Invoice management, payment tracking, medicine catalog |
| **Patient** | `/dashboard/` | Appointments, prescriptions, invoices, lab reports, AI assistant |

---

## Development Workflow

### Code Organization

The project follows Django's app-based modularity:

- **Template-based views** handle server-rendered HTML pages (staff and patient web interfaces)
- **DRF ViewSets** provide the JSON REST API for programmatic access
- **Signals** automate cross-app workflows (invoice generation, audit logging)
- **Middleware** provides request-scoped context (current user for audit)

### Key Design Patterns

1. **Dual Authentication**: Session-based for web UI + JWT for API
2. **Signal-Driven Automation**: `billing.signals` auto-creates invoices; `audit.signals` logs all mutations
3. **Cloudinary Fallback**: Uses Cloudinary when credentials are present, local `FileSystemStorage` otherwise
4. **Database Flexibility**: PostgreSQL in production (via `DATABASE_URL`), SQLite for local development

### Static Files

```bash
# Collect static files for production
cd backend
python manage.py collectstatic --no-input
```

Static files are served via WhiteNoise with `CompressedManifestStaticFilesStorage` (gzip + fingerprint hashing).

### Creating Migrations

```bash
cd backend
python manage.py makemigrations
python manage.py migrate
```

---

## Testing

ProClinic includes a comprehensive test suite with **115+ test cases** covering models, API endpoints, permissions, signals, and middleware.

### Running Tests

```bash
cd backend

# Run all tests
python manage.py test

# Run specific test modules
python manage.py test api.tests                  # Patient API tests (55+ cases)
python manage.py test api.tests_extended          # Staff API, audit, model tests (60+ cases)

# Run with verbosity
python manage.py test --verbosity=2

# Run a specific test class
python manage.py test api.tests.PatientAppointmentTests
```

### Test Coverage Areas

| Test Module | Cases | Coverage |
|---|---|---|
| `api/tests.py` | 55+ | Patient profile, appointments, prescriptions, invoices, lab reports, visits, staff API permissions |
| `api/tests_extended.py` | 60+ | Audit middleware, audit signals, publication model/API, appointment model, lab report model, staff CRUD API, pagination, filtering |

### Test Categories

- **Patient API Tests**: Profile CRUD, appointment booking/cancel/reschedule, double-booking prevention, prescription access, invoice isolation, lab report upload/validation, visit history
- **Staff API Tests**: Pagination, filtering by status/doctor/patient, search, CRUD operations
- **Permission Tests**: Role-based access enforcement (patient blocked from staff endpoints, doctor blocked from admin actions)
- **Audit Tests**: Middleware user capture, signal-based create/update/delete logging, diff computation, sensitive field exclusion
- **Model Tests**: Business logic methods (cancel, reschedule, approve, reject, verify, archive), string representations, status transitions
- **Publication Tests**: Approval/rejection workflow, public listing filtering, web view access control

---

## API Overview

The REST API uses Django REST Framework with JWT authentication. All endpoints are prefixed with `/api/`.

### Authentication Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/token/` | Obtain JWT access + refresh token pair |
| `POST` | `/api/token/refresh/` | Refresh an expired access token |

**Example — Obtain Token:**
```bash
curl -X POST http://localhost:8000/api/token/ \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "Admin@12345"}'
```

**Response:**
```json
{
  "access": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
}
```

### Staff API Endpoints (JWT — Staff roles only)

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/patients/` | List patients (paginated, filterable, searchable) |
| `GET` | `/api/patients/{id}/` | Retrieve patient detail |
| `GET` | `/api/appointments/` | List appointments (filterable by status, doctor, date) |
| `POST` | `/api/appointments/{id}/cancel/` | Cancel an appointment |
| `POST` | `/api/appointments/{id}/reschedule/` | Reschedule an appointment |
| `GET` | `/api/prescriptions/` | List prescriptions (filterable by patient, searchable by medicine) |
| `GET` | `/api/prescriptions/{id}/` | Retrieve prescription detail |
| `GET` | `/api/prescriptions/{id}/pdf/` | Download prescription PDF |
| `GET` | `/api/prescriptions/{id}/html_preview/` | HTML preview of prescription |
| `GET` | `/api/invoices/` | List invoices (filterable by status, patient) |
| `GET` | `/api/invoices/{id}/` | Retrieve invoice detail |
| `GET` | `/api/publications/` | List publications (filterable by status) |
| `POST` | `/api/publications/{id}/approve/` | Approve a publication (Admin only) |
| `POST` | `/api/publications/{id}/reject/` | Reject a publication (Admin only) |
| `GET` | `/api/publications/public_list/` | Public publication listing (no auth) |
| `GET` | `/api/audit/logs/` | List audit logs (Admin only) |

### Patient API Endpoints (JWT — Patient role only)

| Method | Endpoint | Description |
|---|---|---|
| `GET/PUT/PATCH` | `/api/patient/profile/` | View/update own patient profile |
| `GET` | `/api/patient/visits/` | List own visit history |
| `GET/POST` | `/api/patient/appointments/` | List own appointments / Book new |
| `PUT` | `/api/patient/appointments/{id}/reschedule/` | Reschedule own appointment |
| `POST` | `/api/patient/appointments/{id}/cancel/` | Cancel own appointment |
| `GET` | `/api/patient/prescriptions/` | List own prescriptions |
| `GET` | `/api/patient/prescriptions/{id}/` | View own prescription detail |
| `GET` | `/api/patient/invoices/` | List own invoices |
| `GET/POST` | `/api/patient/lab-reports/` | List/upload own lab reports |

### Web Routes (Session-Based)

| Prefix | App | Key Routes |
|---|---|---|
| `/` | core | Home page, Dashboard |
| `/accounts/` | accounts | Login portals, Signup, Profile, Staff management |
| `/patients/` | patients | Patient CRUD, EHR, Lab reports, AI assistant |
| `/appointments/` | appointments | Booking, Doctor schedule, Receptionist management |
| `/prescriptions/` | prescriptions | Create, Pharmacist queue, Dispense |
| `/billing/` | billing | Invoice generation, Management, PDF, Medicine catalog |
| `/publications/` | publications | Submit, Review, Public listing |
| `/audit/` | audit | Audit log viewer |
| `/admin/` | Django Admin | Built-in admin interface |

### Pagination

All list endpoints return paginated responses (default: 20 items per page):

```json
{
  "count": 150,
  "next": "http://localhost:8000/api/patients/?page=2",
  "previous": null,
  "results": [...]
}
```

### Filtering & Search

Endpoints support query parameter filtering via `django-filter`:

```bash
# Filter appointments by status
GET /api/appointments/?status=SCHEDULED

# Filter by doctor
GET /api/appointments/?doctor=3

# Search patients by name
GET /api/patients/?search=John

# Filter invoices by status
GET /api/invoices/?status=UNPAID

# Filter publications by status
GET /api/publications/?status=APPROVED
```

---

## Authentication & Authorization

### Dual Authentication Strategy

ProClinic implements two parallel authentication mechanisms:

1. **Session Authentication** (Web UI): Traditional Django session cookies for template-rendered pages
2. **JWT Authentication** (REST API): SimpleJWT Bearer tokens for programmatic API access

### Token Configuration

| Setting | Value |
|---|---|
| Access Token Lifetime | 60 minutes |
| Refresh Token Lifetime | 1 day |
| Rotate Refresh Tokens | Yes |
| Blacklist After Rotation | Yes |
| Auth Header Type | `Bearer` |

### Role-Based Permission Classes

| Permission Class | Allowed Roles | Usage |
|---|---|---|
| `IsPatient` | `PATIENT` | Patient-facing API endpoints |
| `IsDoctor` | `DOCTOR` | Doctor-specific operations |
| `IsAdminRole` | `ADMIN` | Administrative actions (publication approval, staff management) |
| `IsStaff` | `ADMIN`, `DOCTOR`, `RECEPTIONIST`, `PHARMACIST`, `ACCOUNTANT` | All non-patient endpoints |

### Password Security

- **Primary hasher**: Argon2 (memory-hard, GPU-resistant)
- **Fallback hashers**: PBKDF2, PBKDF2SHA1, BCryptSHA256
- **Validators**: UserAttributeSimilarity, MinimumLength, CommonPassword, NumericPassword

### Patient OTP Recovery

Patients can reset passwords via OTP:
1. Request OTP → sent to registered email via Gmail SMTP
2. Verify OTP (valid for 10 minutes, single-use)
3. Set new password

---

## Configuration Reference

### Django Settings Breakdown

| # | Setting Group | Configuration |
|---|---|---|
| 1 | Environment | `django-environ` for `.env` file parsing |
| 2 | Security | `SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS` from env |
| 3 | Apps | 8 project apps + 4 third-party apps |
| 4 | Middleware | 9 middleware classes (incl. WhiteNoise, CORS, Audit) |
| 5 | Templates | Points to `frontend/templates/` |
| 6 | Database | PostgreSQL (via `DATABASE_URL`) or SQLite fallback |
| 7 | Auth | Custom user model (`accounts.CustomUser`) |
| 8 | Password | Argon2 primary hasher |
| 9 | REST Framework | JWT + Session auth, DjangoFilterBackend, pagination (20/page) |
| 10 | Static | WhiteNoise `CompressedManifestStaticFilesStorage` |
| 11 | Media | Cloudinary (production) or local FileSystem (development) |
| 12 | Timezone | `Asia/Kolkata` (IST) |
| 13 | Email | Gmail SMTP (port 587, TLS) |
| 14 | Logging | Console handler, structured format, stdout output |
| 15 | CORS | `CORS_ALLOW_ALL_ORIGINS = True` |
| 16 | Clinic | Configurable `CONSULTATION_FEE` and `GST_RATE` |

---

## Deployment

### Render (Primary — Blueprint Deploy)

ProClinic includes a `render.yaml` Blueprint for one-click deployment:

1. **Connect Repository**: Push to GitHub, then go to [Render Dashboard](https://dashboard.render.com/) → New → Blueprint
2. **Automatic Provisioning**: Render reads `render.yaml` and creates:
   - Web Service (`proclinic`) — Python runtime, free tier
   - PostgreSQL Database (`proclinic-db`) — free tier, 1 GB storage
3. **Set Environment Variables**: In Render Dashboard → Environment:
   - `DATABASE_URL` (from Render PostgreSQL connection)
   - `CLOUDINARY_CLOUD_NAME`, `CLOUDINARY_API_KEY`, `CLOUDINARY_API_SECRET`
   - Other secrets as needed

**Build Process:**
```bash
# build.sh (runs during Render BUILD phase)
cd backend
pip install --upgrade pip
pip install -r ../requirements.txt
python manage.py collectstatic --no-input
```

**Start Process:**
```bash
# Render START command
cd backend && \
python manage.py migrate --no-input && \
python create_admin.py && \
gunicorn core.wsgi:application --bind 0.0.0.0:$PORT --workers 2 --timeout 120
```

**Production Security** (automatically configured in `render.yaml`):
- `SECURE_SSL_REDIRECT=True`
- `SESSION_COOKIE_SECURE=True`
- `CSRF_COOKIE_SECURE=True`
- `SECURE_HSTS_SECONDS=31536000` (1 year)
- HSTS preloading enabled

### Docker (Self-Hosted)

```bash
# Build and run production container
docker build -t proclinic .
docker run -p 8000:8000 \
  -e DATABASE_URL=postgres://user:pass@db:5432/proclinic \
  -e SECRET_KEY=your-production-secret-key \
  -e DEBUG=False \
  -e ALLOWED_HOSTS=your-domain.com \
  proclinic
```

**Dockerfile highlights:**
- Base: `python:3.12-slim`
- Includes WeasyPrint system dependencies (Pango, Cairo, GDK-Pixbuf)
- Production server: Gunicorn with 2 workers, 120s timeout
- Exposes port 8000

---

## Security Considerations

### Implemented Security Measures

| Category | Implementation |
|---|---|
| **Password Hashing** | Argon2 (primary) with PBKDF2/BCrypt fallbacks |
| **Authentication** | JWT with token rotation and blacklisting |
| **CSRF Protection** | Django CSRF middleware + trusted origins configuration |
| **XSS Prevention** | Django template auto-escaping |
| **Clickjacking** | `X-Frame-Options` via `XFrameOptionsMiddleware` |
| **HTTPS** | `SECURE_SSL_REDIRECT`, `SECURE_PROXY_SSL_HEADER` |
| **HSTS** | 1-year max-age with subdomain inclusion and preloading |
| **Secure Cookies** | `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE` in production |
| **Input Validation** | Model-level `clean()` methods, DRF serializer validation |
| **File Upload Validation** | PDF-only, 5 MB max for lab reports |
| **Audit Trail** | All data mutations logged with actor, timestamp, and diffs |
| **Sensitive Data** | Passwords, tokens, API keys excluded from audit logs |
| **CORS** | `django-cors-headers` (currently allows all origins — restrict in production) |

### Security Recommendations

> [!IMPORTANT]
> Before production deployment, review these items:
> - Set `CORS_ALLOW_ALL_ORIGINS = False` and configure specific allowed origins
> - Rotate `SECRET_KEY` and store in a secrets manager
> - Enable rate limiting on authentication endpoints
> - Set `DEBUG = False` in production
> - Configure `ALLOWED_HOSTS` to include only your production domains

---

## Monitoring & Logging

### Logging Configuration

ProClinic uses structured logging to stdout (compatible with Render, Docker, and cloud log aggregators):

```
[INFO] 2026-05-28 12:00:00 django Starting development server...
[ERROR] 2026-05-28 12:01:00 django.request Internal Server Error: /api/...
[DEBUG] 2026-05-28 12:02:00 accounts User login attempt for admin
```

**Logger Hierarchy:**

| Logger | Level | Description |
|---|---|---|
| `root` | WARNING | Catch-all for unregistered loggers |
| `django` | INFO | Django framework events |
| `django.request` | ERROR | HTTP request errors (4xx/5xx) |
| `accounts` | DEBUG | Authentication events |

### Audit Log Monitoring

The `AuditLog` model provides a built-in activity feed:
- Web UI: `/audit/logs/` (admin-accessible)
- REST API: `GET /api/audit/logs/` (admin-only, paginated)
- Django Admin: Full CRUD interface with search and filters

---

## Troubleshooting

### Common Issues

#### WeasyPrint fails to generate PDFs

**Symptom**: `OSError: cannot load library 'libpango-1.0'`

**Solution**: Install system dependencies:
```bash
sudo apt-get install -y libpango-1.0-0 libpangoft2-1.0-0 libcairo2 libgdk-pixbuf-2.0-0
```

#### Migrations fail with `AppRegistryNotReady`

**Symptom**: `django.core.exceptions.AppRegistryNotReady: Apps aren't loaded yet.`

**Solution**: Ensure `DJANGO_SETTINGS_MODULE` is set:
```bash
export DJANGO_SETTINGS_MODULE=core.settings
```

#### Static files not loading in production

**Symptom**: CSS/JS returns 404 in production.

**Solution**: Run `collectstatic` and ensure WhiteNoise middleware is second in the list:
```bash
cd backend
python manage.py collectstatic --no-input
```

#### Database connection refused (Docker)

**Symptom**: `psycopg2.OperationalError: could not connect to server`

**Solution**: Wait for PostgreSQL health check to pass:
```bash
docker compose up -d db
docker compose exec db pg_isready -U proclinic_user
docker compose up web
```

#### Cloudinary uploads failing

**Symptom**: `cloudinary.exceptions.Error: Must supply cloud_name`

**Solution**: Set all three Cloudinary environment variables. Without them, the app falls back to local `FileSystemStorage`:
```env
CLOUDINARY_CLOUD_NAME=your-cloud-name
CLOUDINARY_API_KEY=your-key
CLOUDINARY_API_SECRET=your-secret
```

#### OTP emails not sending

**Symptom**: Password reset OTP not received.

**Solution**: Configure Gmail SMTP with an [App Password](https://support.google.com/accounts/answer/185833) (not your regular password):
```env
GMAIL_USER=your-email@gmail.com
GMAIL_PASS=your-16-character-app-password
```

#### JWT token expired

**Symptom**: `401 Unauthorized` on API requests.

**Solution**: Refresh the token or obtain a new pair:
```bash
curl -X POST http://localhost:8000/api/token/refresh/ \
  -H "Content-Type: application/json" \
  -d '{"refresh": "your-refresh-token"}'
```

---

## Contributing

### Development Setup

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/your-feature`
3. Follow existing code patterns and conventions
4. Write tests for new functionality
5. Run the full test suite: `python manage.py test`
6. Submit a pull request with a clear description of changes

### Code Standards

| Area | Standard |
|---|---|
| **Python Style** | PEP 8 |
| **Django Convention** | Fat models, thin views |
| **API Design** | RESTful conventions via DRF ViewSets and Routers |
| **Templates** | Component-based with `base.html` inheritance |
| **CSS** | Custom design system (`design-system.css`) |
| **Testing** | Django `TestCase` with `setUpTestData` for performance |
| **Commit Messages** | Clear, descriptive messages with scope |

### Project Apps Overview

| App | Responsibility |
|---|---|
| `accounts` | User model, authentication, role management, OTP recovery |
| `patients` | Patient profiles, EHR visits, lab reports, AI assistant |
| `appointments` | Scheduling, availability, check-in, status management |
| `prescriptions` | Medication plans, PDF generation, pharmacy dispensing |
| `billing` | Invoicing, payment tracking, medicine catalog, PDF export |
| `publications` | Research paper submission and admin review workflow |
| `audit` | Automatic mutation logging via signals and middleware |
| `api` | REST API layer, serializers, permissions, filters, pagination |

---

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.

---

## Credits & Acknowledgements

- **Django** — High-level Python web framework
- **Django REST Framework** — Toolkit for building Web APIs
- **WeasyPrint** — Visual rendering engine for HTML/CSS to PDF
- **Cloudinary** — Cloud-based media management
- **Argon2** — Memory-hard password hashing function (PHC winner)
- **Google Gemini** — Generative AI for the patient health assistant
- **Render** — Cloud application hosting platform
- **WhiteNoise** — Simplified static file serving for Python web apps

---

<div align="center">

**Built with ❤️ for modern healthcare management**

[⬆ Back to Top](#-proclinic)

</div>
]]>
