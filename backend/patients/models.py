from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


class Patient(models.Model):
    BLOOD_GROUP_CHOICES = [
        ('A+', 'A+'), ('A-', 'A-'), ('B+', 'B+'), ('B-', 'B-'),
        ('O+', 'O+'), ('O-', 'O-'), ('AB+', 'AB+'), ('AB-', 'AB-'),
    ]

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='patient_profile',
    )
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    date_of_birth = models.DateField()
    gender = models.CharField(max_length=10, choices=[('Male', 'Male'), ('Female', 'Female'), ('Other', 'Other')])
    blood_group = models.CharField(max_length=5, choices=BLOOD_GROUP_CHOICES)
    contact_number = models.CharField(max_length=15)
    email = models.EmailField(unique=True, blank=True, null=True)
    address = models.TextField()
    allergies = models.TextField(blank=True, help_text="List known allergies")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.first_name} {self.last_name}"


class Visit(models.Model):
    """EHR visit record – written by doctors/staff, read-only for patients."""
    patient = models.ForeignKey(
        Patient, on_delete=models.CASCADE, related_name='visits',
    )
    doctor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='doctor_visits',
    )
    appointment = models.OneToOneField(
        'appointments.Appointment',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='visit',
    )
    visit_date = models.DateTimeField(default=timezone.now)
    notes = models.TextField(blank=True)
    diagnosis = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-visit_date']

    def __str__(self):
        return f"Visit for {self.patient} on {self.visit_date:%Y-%m-%d}"


def _validate_lab_report_pdf(value):
    """Validate uploaded lab report: PDF only, max 5 MB."""
    max_size = 5 * 1024 * 1024  # 5 MB

    if value.size > max_size:
        raise ValidationError(
            f"File size must not exceed 5 MB. "
            f"Your file is {value.size / (1024 * 1024):.1f} MB."
        )

    ext = '.' + value.name.rsplit('.', 1)[-1].lower() if '.' in value.name else ''
    if ext != '.pdf':
        raise ValidationError(
            "Only PDF files are accepted for lab reports. "
            f"Received: '{ext or 'no extension'}'."
        )


from django.core.files.storage import storages

def select_raw_storage():
    return storages['raw']


class LabReport(models.Model):
    """
    Lab report PDF uploaded for a patient.

    Lifecycle:  PENDING → VERIFIED (by a doctor/admin) → ARCHIVED
    """

    STATUS_PENDING = 'pending'
    STATUS_VERIFIED = 'verified'
    STATUS_ARCHIVED = 'archived'

    STATUS_CHOICES = [
        (STATUS_PENDING,  'Pending'),
        (STATUS_VERIFIED, 'Verified'),
        (STATUS_ARCHIVED, 'Archived'),
    ]

    # ── Core relationships ────────────────────────────────────────────────
    patient = models.ForeignKey(
        Patient,
        on_delete=models.CASCADE,
        related_name='lab_reports',
    )
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='uploaded_lab_reports',
    )
    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='verified_lab_reports',
    )

    # ── Report details ────────────────────────────────────────────────────
    test_name = models.CharField(
        max_length=255,
        help_text="Name of the lab test (e.g. CBC, Lipid Panel).",
    )
    report_date = models.DateField(
        help_text="Date the test was conducted.",
    )
    pdf_file = models.FileField(
        upload_to='lab_reports/%Y/%m/',
        storage=select_raw_storage,
        validators=[_validate_lab_report_pdf],
        help_text="Upload the lab report PDF (max 5 MB).",
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
        db_index=True,
    )

    # ── Timestamps ────────────────────────────────────────────────────────
    uploaded_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-uploaded_at']
        verbose_name = 'Lab Report'
        verbose_name_plural = 'Lab Reports'

    def __str__(self):
        return f"{self.test_name} — {self.patient} ({self.report_date})"

    # ── Business logic ────────────────────────────────────────────────────

    def mark_verified(self, user):
        """Mark this report as verified by the given staff user."""
        self.status = self.STATUS_VERIFIED
        self.verified_by = user
        self.save(update_fields=['status', 'verified_by', 'updated_at'])

    def mark_archived(self):
        """Archive this report (soft-delete equivalent)."""
        self.status = self.STATUS_ARCHIVED
        self.save(update_fields=['status', 'updated_at'])