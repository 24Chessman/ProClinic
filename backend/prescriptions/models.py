from django.db import models
from django.conf import settings
from patients.models import Patient, Visit
from appointments.models import Appointment

from django.core.files.storage import storages

def select_raw_storage():
    return storages['raw']

class Prescription(models.Model):
    """
    A prescription issued by a doctor during a clinical visit.

    The Visit model is the canonical holder of diagnosis and clinical notes.
    Prescription stores the medication plan that results from that visit.
    """
    # Primary clinical link — every prescription belongs to a Visit
    visit = models.ForeignKey(
        Visit,
        on_delete=models.CASCADE,
        related_name='prescriptions',
        null=True,
        blank=True,
        help_text="The clinical visit during which this prescription was issued.",
    )

    # Denormalised convenience fields (derived from Visit but kept for fast queries)
    patient = models.ForeignKey(
        Patient,
        on_delete=models.CASCADE,
        related_name='prescriptions',
    )
    doctor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='prescriptions_written',
    )

    # Kept nullable for backward-compat; new prescriptions link via visit instead
    appointment = models.OneToOneField(
        Appointment,
        on_delete=models.SET_NULL,
        related_name='prescription',
        null=True,
        blank=True,
    )

    # PDF export
    pdf_file = models.FileField(upload_to='prescriptions/pdfs/', storage=select_raw_storage, blank=True, null=True)

    # Pharmacist dispense tracking
    DISPENSE_PENDING = 'PENDING'
    DISPENSE_DISPENSED = 'DISPENSED'
    DISPENSE_STATUS_CHOICES = [
        (DISPENSE_PENDING, 'Pending Dispense'),
        (DISPENSE_DISPENSED, 'Dispensed'),
    ]
    dispense_status = models.CharField(
        max_length=20,
        choices=DISPENSE_STATUS_CHOICES,
        default=DISPENSE_PENDING,
        db_index=True,
        help_text='Tracks whether the pharmacist has dispensed medicines.',
    )
    dispensed_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Prescription for {self.patient} - {self.created_at.date()}"


class PrescriptionItem(models.Model):
    prescription = models.ForeignKey(Prescription, on_delete=models.CASCADE, related_name='items')
    medicine_name = models.CharField(max_length=255)
    dosage = models.CharField(max_length=100, help_text="e.g., 500mg")
    instructions = models.CharField(max_length=255, help_text="e.g., Once daily after food")
    duration = models.CharField(max_length=100, help_text="e.g., 5 days")

    def __str__(self):
        return f"{self.medicine_name} for {self.prescription.patient}"