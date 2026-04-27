# ProClinic System Walkthrough & Documentation

## 1. Project Overview
**ProClinic** is a comprehensive, monolithic Hospital Management System (HMS) built to streamline clinical and administrative operations. 

**Main Purpose:**
The system bridges the gap between patient self-service and hospital administration, providing a unified platform where medical staff (Doctors, Pharmacists) and administrative staff (Receptionists, Accountants) can manage the entire patient lifecycle—from booking an appointment to issuing prescriptions and collecting payments.

**High-Level Features:**
- Role-based staff portals and a dedicated Patient Self-Service Portal.
- Appointment scheduling with automated conflict resolution and "No Show" tracking.
- Electronic Health Records (EHR) and Lab Report management.
- Integrated pharmacy prescription and dispensing workflow.
- Automated billing, invoice generation, and PDF downloads.
- REST API layer for patient mobile/web integrations.

---

## 2. Tech Stack
- **Backend Framework:** Django 5.x, Django REST Framework (DRF)
- **Frontend:** Vanilla HTML5, CSS3, JavaScript (no heavy JS framework to ensure maximum speed and minimal payload). UI enriched with Feather Icons.
- **Database:** SQLite (Development) / PostgreSQL (Production via Render)
- **Storage:** Cloudinary (Configured for `raw` PDF uploads and secure delivery)
- **Authentication:** Django Session Auth (Staff/Frontend) + SimpleJWT (APIs)
- **Deployment:** Render (PaaS) with automated build scripts.

---

## 3. User Roles & Permissions

| Role | Responsibilities & Access |
|---|---|
| **PATIENT** | Accesses the self-service portal (via Web or API). Can book/cancel appointments, view prescriptions, view bills, and upload lab reports. Cannot access staff UI. |
| **DOCTOR** | Clinical access. Manages their own appointments, views their patients' EHR, writes prescriptions, reviews and verifies patient lab reports, and submits research publications. |
| **RECEPTIONIST** | Front-desk operations. Books appointments for any patient, checks patients in, and views basic patient profiles. No access to clinical verification or billing creation. |
| **ACCOUNTANT** | Financial operations. Generates invoices from prescriptions/consultations, manages the medicine catalog, updates payment statuses, and views revenue dashboards. |
| **ADMIN** | Superuser access. Can manage staff accounts, archive clinical records, bypass role restrictions, and oversee the entire system. |

---

## 4. System Architecture
ProClinic follows a classic **Model-View-Template (MVT)** architecture for the frontend portal, paired with a decoupled **REST API** layer tailored for the Patient mobile/app experience.

- **Frontend to Backend:** Views handle business logic, enforcing Role-Based Access Control (RBAC) via custom decorators (e.g., `@role_required(['DOCTOR'])`).
- **File Flow:** When a user uploads a PDF (e.g., Lab Report, Invoice), Django relays the file to Cloudinary using the `cloudinary_storage` backend configured for `raw` resources, ensuring PDFs are not compressed or corrupted like images.
- **Security:** CSRF tokens protect all form submissions. JWTs secure all API endpoints.

---

## 5. Module-by-Module Walkthrough

### 5.1 Accounts (`accounts`)
- **Purpose:** Handles custom user modeling and authentication.
- **Models:** `CustomUser` (inherits `AbstractUser`, adds `role`, `phone_number`, `specialization`).
- **Rules:** Users are routed to different dashboards upon login based on their role.

### 5.2 Patients & EHR (`patients`)
- **Purpose:** Central repository for patient demographics and clinical history.
- **Main Views:** `patient_detail` (EHR view), `doctor_lab_reports`, `lab_report_verify`.
- **Logic:** Lab reports uploaded by patients are marked as "Pending". Only Doctors/Admins can click "Verify". Doctors receive an email notification when their patients upload reports.

### 5.3 Appointments (`appointments`)
- **Purpose:** Scheduling and queue management.
- **Models:** `Appointment`, `DoctorUnavailability`.
- **Validation:** Strict time-collision logic prevents double-booking a doctor. Doctors can block out unavailable times. "No Show" statuses are automatically applied if patients miss slots.

### 5.4 Prescriptions (`prescriptions`)
- **Purpose:** Pharmacy workflow.
- **Flow:** Doctor creates a prescription -> It appears in the Patient's EHR -> It appears in the Accountant's draft invoice queue -> Pharmacist marks it "Dispensed".

### 5.5 Billing & Invoices (`billing`)
- **Purpose:** Financial tracking.
- **Models:** `Invoice`, `InvoiceItem`, `MedicineMaster`.
- **Flow:** Accountants convert "Draft" invoices (auto-generated from prescriptions) into final bills. Patients download the generated PDFs. Uses ₹ (INR) currency exclusively.

### 5.6 Publications (`publications`)
- **Purpose:** Academic research management for doctors.
- **Flow:** Doctors upload research PDFs -> Admins review and approve/reject them.

---

## 6. API Documentation

ProClinic exposes a secure REST API under `/api/patient/` for patient self-service applications.

### Authentication
- `POST /api/token/`: Submit username/password to receive JWT access/refresh tokens.
- `POST /api/token/refresh/`: Refresh an expired access token.

### Patient Endpoints (Requires JWT Auth & PATIENT role)
- `GET /api/patient/profile/`: Fetch the logged-in patient's demographic details.
- `GET /api/patient/appointments/`: List all appointments for the patient.
- `POST /api/patient/appointments/`: Book a new appointment (requires `doctor`, `date`, `time`).
- `POST /api/patient/appointments/<id>/cancel/`: Cancel an upcoming appointment.
- `GET /api/patient/prescriptions/`: View issued prescriptions.
- `GET /api/patient/invoices/`: View billing history and payment statuses.
- `GET / POST /api/patient/lab-reports/`: View or upload lab reports (multipart/form-data for PDF uploads).

*Note: The API strictly enforces ownership. A patient cannot access another patient's records (returns 403 Forbidden or 404 Not Found).*

---

## 7. Frontend Pages / Templates

- **Dashboards (`dashboards/`)**: Dynamic landing pages. The context passed to `dashboard.html` changes entirely based on the user's role (e.g., Revenue for Accountants, Queue for Receptionists, Lab Reports for Doctors).
- **Patient EHR (`patients/patient_detail.html`)**: The core clinical screen. Uses tabbed navigation (Visits, Prescriptions, Lab Reports, Invoices) to present a holistic view of the patient without page reloads.
- **Invoice Generation (`billing/generate_invoice.html`)**: A highly interactive vanilla JS form allowing accountants to add line items dynamically, calculating Subtotals, Taxes, Discounts, and Grand Totals in real-time.
- **PDF Templates (`billing/pdf/`)**: Clean HTML templates that are rendered to string and converted to downloadable files for invoices and receipts.

---

## 8. Core Data Models

1. **`Patient`**: Links to a `CustomUser`. Stores `dob`, `blood_group`, `address`.
2. **`Appointment`**: Relates `Patient` to `Doctor` (CustomUser). Fields: `scheduled_time`, `status` (Scheduled, Checked-In, Completed, Cancelled, No Show).
3. **`Prescription` & `PrescriptionItem`**: Relates `Appointment` to medications. Stores dosage, duration, and dispensing status.
4. **`Invoice`**: Relates to `Patient` and optionally `Appointment`. Calculates financials.
5. **`LabReport`**: Relates to `Patient`. Stores `test_name`, `pdf_file`, `status` (Pending, Verified, Archived), and `verified_by`.

---

## 9. Key Workflows

### The Clinical Consultation Flow
1. **Booking**: Patient books online or Receptionist books via the staff portal.
2. **Arrival**: Receptionist marks the appointment as `CHECKED_IN`.
3. **Consultation**: Doctor clicks "New Prescription", selects the patient. The system allows the doctor to click a link to view the patient's EHR & Lab Reports in a new tab.
4. **Prescribing**: Doctor adds medicines to the prescription form and saves. The appointment is marked `COMPLETED`.
5. **Billing**: An invoice `DRAFT` is automatically generated. The Accountant opens the draft, clicks "Load Prescribed Medicines", adds consultation fees, and finalizing the bill.
6. **Payment**: Patient pays at the reception, Accountant marks the bill as `PAID`.

---

## 10. Validation and Permissions

- **Field-Level**: Time slots are validated to ensure they fall within hospital working hours (9 AM - 5 PM). File uploads validate against max size (5MB) and extension (`.pdf`).
- **Role-Based Restrictions (View Level)**: Views are wrapped in logic that checks `request.user.role`. For example, if a Receptionist attempts to POST to the `lab_report_verify` endpoint, the server safely aborts and redirects with an error message.
- **Ownership Restrictions (Query Level)**: Doctors querying lab reports use `.filter(patient__appointments__doctor=request.user)`. Patients querying APIs use `.filter(patient=request.user.patient_profile)`. This guarantees data isolation.

---

## 11. File Upload / Storage (Cloudinary)

ProClinic relies heavily on PDF documents for medical integrity.
- **Configuration:** ProClinic overrides standard Django storage with `CloudinaryStorage`.
- **PDF Handling:** In `settings.py` and model fields, files are explicitly tagged as `RESOURCE_TYPE_RAW`. If this is omitted, Cloudinary attempts to process PDFs as images, causing `save()` attribute errors and breaking downloads.
- **Production vs Local:** In local development, if `CLOUDINARY_URL` is omitted, the system falls back to the local `/media/` folder gracefully. On Render, the environment variable enforces cloud storage since Render's free tier uses ephemeral disks.

---

## 12. Deployment Notes

- **Platform:** Render (Web Service).
- **Environment Variables Required:** `SECRET_KEY`, `DEBUG=False`, `DATABASE_URL` (Postgres), `CLOUDINARY_URL`.
- **Build Script (`build.sh`):** Executes `pip install`, `collectstatic`, and `migrate`.
- **Superuser Management:** An idempotent `create_admin.py` script runs post-deployment to ensure the default `admin` user is guaranteed to exist with the `ADMIN` role, preventing lockouts in production.
- **Caveat:** Because Render spins down free instances after inactivity, initial API requests or page loads may take ~50 seconds to "wake up" the server.

---

## 13. Testing

ProClinic maintains a robust automated test suite.
- **Command:** `python manage.py test`
- **Coverage:** 
  - Validates API endpoints (e.g., ensuring Patients get 403 Forbidden when trying to access staff endpoints).
  - Validates model logic (e.g., ensuring `DoctorUnavailability` successfully blocks appointment creation).
- **Limitations / Manual Testing Needed:** Tests that interact with `FileField` models (like Lab Reports and Publications) require a live Cloudinary API key. If run locally without keys, 3 specific file-upload tests will fail. 

---

## 14. Future Improvements

1. **Payment Gateway Integration:** Currently, online payments are mocked. Integrating Stripe or Razorpay would allow patients to pay their `UNPAID` invoices directly from the portal.
2. **Telemedicine / Video Consults:** Integrating WebRTC or Zoom APIs for virtual appointments.
3. **SMS/WhatsApp Notifications:** While fail-silent email notifications exist (e.g., notifying doctors of lab uploads), SMS via Twilio would improve patient attendance and reduce "No Shows".
4. **Pagination:** Adding backend pagination to tables (like Invoices and Visits) to improve load times as the database scales to thousands of records.

---

## 15. Conclusion

ProClinic is a highly functional, secure, and production-ready hospital management system. By strictly enforcing role-based boundaries and relying on a monolithic architecture, it achieves high reliability and ease of deployment. The recent stabilization efforts—securing Cloudinary raw uploads, fixing template currency formatting, implementing doctor notifications, and refining the REST API—have transformed the codebase into a resilient platform capable of handling real-world clinic workflows efficiently.
