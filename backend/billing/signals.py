"""
billing/signals.py
──────────────────
Post-save signal that creates a DRAFT invoice whenever an Appointment
transitions to COMPLETED status.

The draft is pre-populated with:
  • A single CONSULTATION line item (fee from settings.CONSULTATION_FEE).
  • One MEDICINE line item per PrescriptionItem linked via the Visit,
    priced from MedicineMaster (defaults to $0.00 if not found — accountant
    corrects in the review step).

If the appointment already has an invoice (e.g. manually generated), the
signal is a no-op. All exceptions are caught and logged so a signal failure
never prevents the appointment save from completing.
"""

import logging

from django.db.models.signals import post_save
from django.dispatch import receiver

from appointments.models import Appointment
from billing.models import Invoice, InvoiceItem, MedicineMaster
from billing.utils import get_consultation_fee

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Appointment)
def create_draft_invoice_on_completion(sender, instance, created, **kwargs):
    """Create a DRAFT invoice when an appointment is marked COMPLETED."""

    # Only react to updates, not initial creation
    if created:
        return

    if instance.status != 'COMPLETED':
        return

    # Guard: a manual invoice may already exist (OneToOneField on appointment)
    if Invoice.objects.filter(appointment=instance).exists():
        return

    try:
        invoice = Invoice.objects.create(
            patient=instance.patient,
            appointment=instance,
            status='DRAFT',
            subtotal=0,
            tax_amount=0,
            discount_amount=0,
            grand_total=0,
            total_amount=0,
            paid_amount=0,
            due_amount=0,
        )

        # ── Consultation line item ─────────────────────────────────────────
        fee = get_consultation_fee()
        InvoiceItem.objects.create(
            invoice=invoice,
            item_type='CONSULTATION',
            service_name='General Consultation',
            unit_cost=fee,
            quantity=1,
        )

        # ── Medicine line items from prescription via Visit ─────────────────
        # Visit → Prescription → PrescriptionItems
        # Silently skipped if no visit or prescription exists.
        try:
            visit = instance.visit  # OneToOneField reverse; raises if missing
            for presc in visit.prescriptions.all():
                for item in presc.items.all():
                    try:
                        med = MedicineMaster.objects.get(name__iexact=item.medicine_name)
                        price = med.default_price
                    except MedicineMaster.DoesNotExist:
                        price = 0  # Accountant corrects this in the review step

                    InvoiceItem.objects.create(
                        invoice=invoice,
                        item_type='MEDICINE',
                        service_name=item.medicine_name,
                        notes=f"{item.dosage} \u2013 {item.instructions} ({item.duration})",
                        unit_cost=price,
                        quantity=1,
                    )
        except Exception:
            # No Visit / no Prescription is perfectly valid; accountant adds
            # medicine items manually during the draft review step.
            pass

        # Recompute all financial summaries from the created line items
        invoice.recalculate_totals()
        invoice.save()

        logger.info(
            "Draft invoice #%s created for appointment #%s (patient: %s).",
            invoice.pk, instance.pk, instance.patient,
        )

    except Exception as e:
        # Never let a signal failure break the appointment save
        logger.error(
            "Failed to create draft invoice for appointment #%s: %s",
            instance.pk, e,
        )
