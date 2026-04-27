"""
billing/utils.py
────────────────
Utilities for the billing module: decimal parsing, consultation fee, and
WeasyPrint-based PDF generation.

PDF generation is intentionally done in-memory (BytesIO / ContentFile) and
served directly as an HttpResponse. We do NOT rely on CloudinaryResource.save()
because CloudinaryField values are Cloudinary descriptors, not FieldFile objects,
and have no .save() method.  If we want to cache the PDF we use Django's own
FileField.save() which writes to the configured DEFAULT_FILE_STORAGE backend.
"""
from __future__ import annotations

import logging
from datetime import date
from decimal import Decimal, InvalidOperation
from io import BytesIO

from django.conf import settings
from django.core.files.base import ContentFile
from django.http import HttpResponse
from django.template.loader import render_to_string

logger = logging.getLogger(__name__)

_INVOICE_TEMPLATE = "billing/invoice_pdf_template.html"


def get_consultation_fee():
    """Return the configured consultation fee.

    Reads CONSULTATION_FEE from Django settings (set in settings.py or via
    environment), falling back to ₹500.00 if not configured.
    """
    return Decimal(str(getattr(settings, 'CONSULTATION_FEE', '500.00')))


def _parse_decimal(val, default='0'):
    """Safely parse a value into a Decimal, returning Decimal(default) on failure."""
    try:
        return Decimal(str(val).strip() or default)
    except (InvalidOperation, TypeError, ValueError):
        return Decimal(default)


# ── Invoice PDF generation ────────────────────────────────────────────────────

def _build_invoice_context(invoice) -> dict:
    return {
        "invoice": invoice,
        "items": list(invoice.items.all().order_by("id")),
        "issued_date": invoice.created_at.strftime("%d %B %Y"),
    }


def render_invoice_html(invoice) -> str:
    """Render the invoice PDF template to an HTML string."""
    return render_to_string(_INVOICE_TEMPLATE, _build_invoice_context(invoice))


def generate_invoice_pdf_bytes(invoice) -> bytes:
    """
    Render the invoice as a PDF and return the raw bytes.

    Uses WeasyPrint to convert the HTML template to PDF entirely in memory.
    Raises RuntimeError if WeasyPrint is not installed or rendering fails.
    """
    try:
        from weasyprint import HTML as WeasyHTML  # lazy import
    except ImportError as e:
        logger.error("WeasyPrint is not installed — cannot generate invoice PDF.")
        raise RuntimeError("WeasyPrint is not installed.") from e

    html_string = render_invoice_html(invoice)

    try:
        pdf_bytes = WeasyHTML(string=html_string).write_pdf()
    except Exception as exc:
        logger.exception("WeasyPrint failed for invoice %s: %s", invoice.pk, exc)
        raise RuntimeError(f"WeasyPrint failed: {str(exc)}") from exc

    return pdf_bytes


def generate_invoice_pdf(invoice):
    """
    Generate a PDF for the given invoice.

    Strategy:
      1. If invoice.pdf_file already exists and is readable (cached on disk /
         default storage), return it so the caller can stream it.
      2. Otherwise generate fresh bytes with WeasyPrint, save them using
         Django's standard FileField.save() (NOT CloudinaryResource.save()),
         and return the updated FileField.

    Returns the FileField descriptor on success.
    Raises RuntimeError on generation failure.
    """
    # ── 1. Serve cached file if readable ─────────────────────────────────────
    if invoice.pdf_file:
        try:
            # .open() is available on Django FieldFile objects; skip if it fails
            invoice.pdf_file.open('rb')
            invoice.pdf_file.close()
            return invoice.pdf_file
        except Exception:
            pass  # cached file missing or unreadable — fall through to regen

    # ── 2. Generate fresh PDF bytes in memory ────────────────────────────────
    pdf_bytes = generate_invoice_pdf_bytes(invoice)

    filename = f"invoice_{invoice.pk}_{date.today().isoformat()}.pdf"

    # Use Django's FileField.save() — this writes to DEFAULT_FILE_STORAGE
    # (local filesystem or any configured backend) and is NOT a Cloudinary call.
    invoice.pdf_file.save(filename, ContentFile(pdf_bytes), save=True)
    logger.info("Saved PDF for invoice %s → %s", invoice.pk, invoice.pdf_file.name)
    return invoice.pdf_file


def invoice_pdf_response(invoice) -> HttpResponse:
    """Generate (or serve cached) invoice PDF as an attachment HttpResponse."""
    if invoice.pdf_file:
        try:
            with invoice.pdf_file.open("rb") as fh:
                return _make_invoice_response(fh.read(), invoice)
        except Exception:
            pass  # cached file missing on disk — re-generate

    pdf_bytes = generate_invoice_pdf_bytes(invoice)
    return _make_invoice_response(pdf_bytes, invoice)


def _make_invoice_response(pdf_bytes: bytes, invoice) -> HttpResponse:
    filename = f"invoice_{invoice.pk}.pdf"
    response = HttpResponse(pdf_bytes, content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    response["Content-Length"] = len(pdf_bytes)
    return response

# ── Email Notifications ───────────────────────────────────────────────────────

from django.core.mail import send_mail

def send_draft_invoice_email(invoice):
    """Send an email notification when a draft invoice is generated."""
    patient_email = getattr(invoice.patient, 'email', None)
    if not patient_email:
        logger.info("Skipping draft invoice email for invoice %s: No patient email.", invoice.pk)
        return

    subject = f"Invoice #{invoice.pk} Generated - ProClinic"
    message = (
        f"Dear {invoice.patient.first_name},\n\n"
        f"A new draft invoice (#{invoice.pk}) has been generated for your recent appointment.\n"
        f"Status: Pending Review\n"
        f"Amount: ₹{invoice.grand_total}\n\n"
        f"You can view the details in your patient portal once it is finalized.\n\n"
        f"Thank you,\nProClinic Team"
    )
    
    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[patient_email],
            fail_silently=False,
        )
        logger.info("Successfully sent draft invoice email for invoice %s to %s", invoice.pk, patient_email)
    except Exception as e:
        logger.error("Failed to send draft invoice email for invoice %s: %s", invoice.pk, e)


def send_paid_invoice_email(invoice):
    """Send an email notification when an invoice is marked as PAID."""
    patient_email = getattr(invoice.patient, 'email', None)
    if not patient_email:
        logger.info("Skipping paid invoice email for invoice %s: No patient email.", invoice.pk)
        return

    subject = f"Payment Confirmation for Invoice #{invoice.pk} - ProClinic"
    message = (
        f"Dear {invoice.patient.first_name},\n\n"
        f"We have received your payment of ₹{invoice.paid_amount} for invoice #{invoice.pk}.\n"
        f"The invoice is now marked as PAID.\n\n"
        f"Thank you for choosing ProClinic.\n\n"
        f"Best regards,\nProClinic Team"
    )
    
    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[patient_email],
            fail_silently=False,
        )
        logger.info("Successfully sent paid invoice email for invoice %s to %s", invoice.pk, patient_email)
    except Exception as e:
        logger.error("Failed to send paid invoice email for invoice %s: %s", invoice.pk, e)
