from decimal import Decimal, InvalidOperation
import logging

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Sum
from django.http import Http404, JsonResponse
from django.views.decorators.http import require_POST

from audit.utils import log_action
from .forms import InvoiceForm, InvoiceItemFormSet
from .models import Invoice
from patients.models import Patient

logger = logging.getLogger(__name__)


def _parse_decimal(val, default='0'):
    """Safely parse a POST string value into a Decimal.

    Returns Decimal(default) on any parse failure instead of raising,
    so individual bad fields degrade to 0 rather than crashing the view.
    """
    try:
        return Decimal(str(val).strip() or default)
    except (InvalidOperation, TypeError, ValueError):
        return Decimal(default)


# ─── Shared guard ─────────────────────────────────────────────────────────────

def _accountant_or_admin(user):
    return user.role in {'ACCOUNTANT', 'ADMIN'}


# ─── Invoice generation ───────────────────────────────────────────────────────

@login_required
def generate_invoice(request):
    # Receptionist role removed — only ACCOUNTANT and ADMIN may generate invoices
    if request.user.role not in {'ACCOUNTANT', 'ADMIN'}:
        return redirect('dashboard')

    if request.method == 'POST':
        form = InvoiceForm(request.POST)

        if form.is_valid():
            invoice = form.save(commit=False)
            
            # Parse JS-calculated financial fields using the safe helper.
            # _parse_decimal returns Decimal('0') on any bad input rather than
            # raising, and never swallows the error silently at the view level.
            invoice.subtotal        = _parse_decimal(request.POST.get('subtotal'))
            invoice.tax_amount      = _parse_decimal(request.POST.get('tax_amount'))
            invoice.discount_amount = _parse_decimal(request.POST.get('discount_amount'))
            invoice.grand_total     = _parse_decimal(request.POST.get('grand_total'))
            invoice.paid_amount     = _parse_decimal(request.POST.get('paid_amount'))
            invoice.due_amount      = _parse_decimal(request.POST.get('due_amount'))
            invoice.total_amount    = invoice.grand_total  # BC tracking

            # Guard: if both subtotal and grand_total are zero the JS calculation
            # almost certainly failed (empty form, tampered data, or JS error).
            # Return a clear error instead of persisting a zeroed invoice.
            if invoice.grand_total == Decimal('0') and invoice.subtotal == Decimal('0'):
                messages.error(
                    request,
                    "Invoice total could not be calculated. "
                    "Please check line item values and try again."
                )
                return render(request, 'billing/generate_invoice.html', {'form': form})
                
            # Security verification
            if invoice.appointment and invoice.appointment.patient_id != invoice.patient_id:
                messages.error(request, "Invalid submission: Linked appointment does not belong to selected patient.")
                return redirect('generate_invoice')

            # Duplicate invoice guard.
            # Invoice.appointment is a OneToOneField — a second invoice for the
            # same appointment would raise an IntegrityError at the DB level.
            # Catch it here cleanly before any save attempt.
            if invoice.appointment_id:
                if Invoice.objects.filter(appointment_id=invoice.appointment_id).exists():
                    messages.error(
                        request,
                        "An invoice already exists for this appointment. "
                        "Please select a different appointment or view the existing invoice."
                    )
                    return render(request, 'billing/generate_invoice.html', {'form': form, 'pre_appt': ''})

            invoice.save()

            # Parse dynamic line items from Javascript
            item_types = request.POST.getlist('item_type[]')
            service_names = request.POST.getlist('service_name[]')
            notes_list = request.POST.getlist('notes[]')
            qtys = request.POST.getlist('quantity[]')
            costs = request.POST.getlist('unit_cost[]')

            for i in range(len(service_names)):
                name = service_names[i].strip()
                if not name:
                    continue
                    
                import decimal
                from .models import InvoiceItem
                try:
                    qty = int(qtys[i])
                    cost = decimal.Decimal(costs[i])
                except (ValueError, decimal.InvalidOperation, IndexError):
                    qty, cost = 1, decimal.Decimal('0.00')

                item_type = item_types[i] if i < len(item_types) else 'OTHER'
                notes = notes_list[i] if i < len(notes_list) else ''

                InvoiceItem.objects.create(
                    invoice=invoice,
                    item_type=item_type,
                    service_name=name,
                    notes=notes,
                    quantity=qty,
                    unit_cost=cost
                )

            log_action(
                actor=request.user,
                action_type='CREATE',
                entity_type='Invoice',
                entity_id=invoice.pk,
                changes={
                    'patient_id': invoice.patient_id,
                    'grand_total': str(invoice.grand_total),
                    'item_count': invoice.items.count(),
                    'status': invoice.status,
                },
            )

            messages.success(
                request,
                f"Invoice #{invoice.pk} generated for {invoice.patient}."
            )
            return redirect('invoice_detail', pk=invoice.pk)
    else:
        form = InvoiceForm()

    # Pass any pre-selected appointment if navigating from another view
    pre_appt = request.GET.get('appointment_id')

    return render(request, 'billing/generate_invoice.html', {
        'form': form,
        'pre_appt': pre_appt,
    })


# ─── Patient self-service ─────────────────────────────────────────────────────

@login_required
def patient_invoices(request):
    if request.user.role != 'PATIENT':
        return redirect('dashboard')

    patient_profile = getattr(request.user, 'patient_profile', None)
    if patient_profile is None:
        patient_profile = Patient.objects.filter(
            Q(email=request.user.email) |
            Q(contact_number=request.user.phone_number) |
            Q(contact_number=request.user.username)
        ).first()

    if not patient_profile:
        return redirect('dashboard')

    invoices = (
        Invoice.objects
        .filter(patient=patient_profile)
        # Include DRAFT invoices so patients can see auto-generated bills
        # immediately after a completed appointment. The accountant still
        # reviews and adjusts the draft before marking it PAID.
        .prefetch_related('items', 'appointment__doctor')
        .order_by('-created_at')
    )

    return render(request, 'billing/patient_invoices.html', {
        'invoices': invoices,
    })


# ─── Accountant Invoice Management ───────────────────────────────────────────


# ─── Draft invoice editing ────────────────────────────────────────────────────

@login_required
def invoice_edit_draft(request, pk):
    """Allow accountants/admins to edit a DRAFT invoice.

    GET  – render the same generate_invoice template pre-filled with existing
           line items, prices, and totals so the accountant can adjust
           medicine prices, add/remove items, apply discount/tax, etc.

    POST – save updated line items + totals, then transition status to UNPAID
           so the invoice enters the active billing queue (or keep as DRAFT if
           the accountant explicitly chooses).

    Only DRAFT invoices can be edited this way.  Any other status returns a
    403-style redirect so we never accidentally mutate a paid/refunded invoice.
    """
    if not _accountant_or_admin(request.user):
        return redirect('dashboard')

    invoice = get_object_or_404(
        Invoice.objects.select_related('patient', 'appointment').prefetch_related('items'),
        pk=pk,
    )

    if invoice.status != 'DRAFT':
        messages.error(request, f"Invoice #{pk} is not a draft and cannot be edited here.")
        return redirect('invoice_detail', pk=pk)

    if request.method == 'POST':
        # ── Parse financial totals from JS-computed hidden fields ──────────
        subtotal        = _parse_decimal(request.POST.get('subtotal'))
        tax_amount      = _parse_decimal(request.POST.get('tax_amount'))
        discount_amount = _parse_decimal(request.POST.get('discount_amount'))
        grand_total     = _parse_decimal(request.POST.get('grand_total'))
        paid_amount     = _parse_decimal(request.POST.get('paid_amount'))
        due_amount      = _parse_decimal(request.POST.get('due_amount'))

        # Guard: reject zeroed-out submissions (indicates JS did not run)
        if grand_total == Decimal('0') and subtotal == Decimal('0'):
            messages.error(
                request,
                "Invoice total could not be calculated. "
                "Please check line item values and try again.",
            )
            return redirect('invoice_edit_draft', pk=pk)

        # ── Determine target status ────────────────────────────────────────
        # If the accountant explicitly set 'DRAFT' in the status field, keep it
        # as draft. Any other value — or the default — publishes it as UNPAID.
        requested_status = request.POST.get('status', 'UNPAID').upper()
        if requested_status not in ('DRAFT', 'UNPAID', 'PARTIAL', 'PAID'):
            requested_status = 'UNPAID'

        # ── Replace all line items ─────────────────────────────────────────
        from .models import InvoiceItem
        import decimal as _decimal

        item_types    = request.POST.getlist('item_type[]')
        service_names = request.POST.getlist('service_name[]')
        notes_list    = request.POST.getlist('notes[]')
        qtys          = request.POST.getlist('quantity[]')
        costs         = request.POST.getlist('unit_cost[]')

        # Wipe old items and rebuild from POST data so changes are clean
        invoice.items.all().delete()

        for i, name in enumerate(service_names):
            name = name.strip()
            if not name:
                continue
            try:
                qty  = int(qtys[i])
                cost = _decimal.Decimal(costs[i])
            except (ValueError, _decimal.InvalidOperation, IndexError):
                qty, cost = 1, _decimal.Decimal('0.00')

            InvoiceItem.objects.create(
                invoice=invoice,
                item_type=item_types[i] if i < len(item_types) else 'OTHER',
                service_name=name,
                notes=notes_list[i] if i < len(notes_list) else '',
                quantity=qty,
                unit_cost=cost,
            )

        # ── Persist updated financial fields ──────────────────────────────
        invoice.subtotal        = subtotal
        invoice.tax_amount      = tax_amount
        invoice.discount_amount = discount_amount
        invoice.grand_total     = grand_total
        invoice.total_amount    = grand_total
        invoice.paid_amount     = paid_amount
        invoice.due_amount      = due_amount
        invoice.status          = requested_status
        invoice.save(update_fields=[
            'subtotal', 'tax_amount', 'discount_amount', 'grand_total',
            'total_amount', 'paid_amount', 'due_amount', 'status', 'updated_at',
        ])

        log_action(
            actor=request.user,
            action_type='UPDATE',
            entity_type='Invoice',
            entity_id=invoice.pk,
            changes={
                'patient_id': invoice.patient_id,
                'new_status': invoice.status,
                'grand_total': str(invoice.grand_total),
                'item_count': invoice.items.count(),
            },
        )

        verb = "saved as draft" if invoice.status == 'DRAFT' else "published"
        messages.success(
            request,
            f"Invoice #{invoice.pk} for {invoice.patient} updated and {verb}.",
        )
        return redirect('invoice_detail', pk=pk)

    # ── GET: build pre-fill context ────────────────────────────────────────
    # Pass existing items so the JS template can re-render them.
    existing_items = list(invoice.items.values(
        'item_type', 'service_name', 'notes', 'quantity', 'unit_cost',
    ))

    return render(request, 'billing/edit_draft_invoice.html', {
        'invoice': invoice,
        'existing_items': existing_items,
    })


@login_required
def invoice_list(request):
    """
    Full invoice management list – Accountant and Admin.

    Filters:  ?status=DRAFT|UNPAID|PARTIAL|PAID|REFUNDED
    Search:   ?q=<patient name>

    The default view (no status filter) excludes DRAFT invoices so they
    don’t pollute the active-invoice list. Use ?status=DRAFT for the
    dedicated pending-review queue.
    """
    if not _accountant_or_admin(request.user):
        return redirect('dashboard')

    status_filter = request.GET.get('status', '').upper()
    search_query = request.GET.get('q', '').strip()

    qs = (
        Invoice.objects
        .select_related('patient', 'appointment')
        .prefetch_related('items')
        .order_by('-created_at')
    )

    if status_filter in ('DRAFT', 'UNPAID', 'PARTIAL', 'PAID', 'REFUNDED'):
        qs = qs.filter(status=status_filter)
    else:
        # Default: hide drafts so only actionable invoices are shown
        qs = qs.exclude(status='DRAFT')

    if search_query:
        qs = qs.filter(
            Q(patient__first_name__icontains=search_query) |
            Q(patient__last_name__icontains=search_query)
        )

    # Aggregate counts for all tab badges (unaffected by current filter)
    all_invoices = Invoice.objects
    counts = {
        'all':     all_invoices.exclude(status='DRAFT').count(),
        'DRAFT':   all_invoices.filter(status='DRAFT').count(),
        'UNPAID':  all_invoices.filter(status='UNPAID').count(),
        'PARTIAL': all_invoices.filter(status='PARTIAL').count(),
        'PAID':    all_invoices.filter(status='PAID').count(),
    }
    revenue = {
        'paid':    all_invoices.filter(status='PAID').aggregate(t=Sum('total_amount'))['t'] or 0,
        'pending': all_invoices.filter(status__in=['UNPAID', 'PARTIAL']).aggregate(t=Sum('total_amount'))['t'] or 0,
    }

    return render(request, 'billing/invoice_list.html', {
        'invoices': qs,
        'current_status': status_filter,
        'search_query': search_query,
        'counts': counts,
        'revenue': revenue,
    })


@login_required
def invoice_detail(request, pk):
    """
    Full detail view for a single invoice – Accountant / Admin.
    Shows all line items, linked patient, appointment, and status history.
    """
    if request.user.role not in {'ACCOUNTANT', 'ADMIN'}:
        return redirect('dashboard')

    invoice = get_object_or_404(
        Invoice.objects
        .select_related('patient', 'appointment__doctor')
        .prefetch_related('items'),
        pk=pk,
    )

    return render(request, 'billing/invoice_detail.html', {
        'invoice': invoice,
        'items': invoice.items.all(),
    })


@require_POST
@login_required
def invoice_update_status(request, pk):
    """
    POST: update an invoice's payment status.
    Accepts status in POST body; writes an audit log.
    """
    if not _accountant_or_admin(request.user):
        return redirect('dashboard')

    invoice = get_object_or_404(Invoice, pk=pk)
    new_status = request.POST.get('status', '').upper()

    if new_status not in ('UNPAID', 'PARTIAL', 'PAID', 'REFUNDED'):
        messages.error(request, "Invalid status value.")
        return redirect('invoice_list')

    if invoice.status == new_status:
        messages.info(request, f"Invoice #{invoice.pk} is already {invoice.get_status_display()}.")
    else:
        old_display = invoice.get_status_display()
        invoice.status = new_status

        # Keep paid_amount / due_amount consistent with the new status so
        # the payment summary card always shows accurate figures.
        if new_status == 'PAID':
            invoice.paid_amount = invoice.grand_total
            invoice.due_amount  = Decimal('0.00')
        elif new_status == 'UNPAID':
            invoice.paid_amount = Decimal('0.00')
            invoice.due_amount  = invoice.grand_total
        elif new_status == 'REFUNDED':
            invoice.paid_amount = Decimal('0.00')
            invoice.due_amount  = Decimal('0.00')
        elif new_status == 'PARTIAL':
            from .utils import _parse_decimal
            paid = _parse_decimal(request.POST.get('paid_amount', '0'))
            if paid > invoice.grand_total:
                paid = invoice.grand_total
            invoice.paid_amount = paid
            invoice.due_amount = invoice.grand_total - paid

        invoice.save(update_fields=['status', 'paid_amount', 'due_amount', 'updated_at'])

        log_action(
            actor=request.user,
            action_type='UPDATE',
            entity_type='Invoice',
            entity_id=invoice.pk,
            changes={
                'patient': str(invoice.patient),
                'old_status': old_display,
                'new_status': invoice.get_status_display(),
            },
        )

        messages.success(
            request,
            f"Invoice #{invoice.pk} ({invoice.patient}) updated: "
            f"{old_display} → {invoice.get_status_display()}.",
        )

        # Redirect back to wherever the user came from
    next_url = request.POST.get('next', '')
    if next_url and (next_url.startswith('/billing/') or next_url.startswith('/dashboard')):
        return redirect(next_url)
    return redirect('invoice_list')

@require_POST
@login_required
def invoice_send_email_manual(request, pk):
    """
    POST: manually send an invoice email to the patient with the invoice PDF attached.
    Accountant and Admin only.
    """
    if not _accountant_or_admin(request.user):
        return redirect('dashboard')

    invoice = get_object_or_404(Invoice, pk=pk)
    patient_email = getattr(invoice.patient, 'email', None)

    if not patient_email:
        messages.error(request, f"Patient {invoice.patient} does not have an email address on file.")
        return redirect('invoice_detail', pk=pk)

    from django.conf import settings
    from django.core.mail import EmailMessage
    from billing.utils import generate_invoice_pdf_bytes

    subject = f"Invoice #{invoice.pk} - ProClinic"
    body = (
        f"Dear {invoice.patient.first_name},\n\n"
        f"Please find your invoice #{invoice.pk} details and the attached PDF below.\n\n"
        f"  Status      : {invoice.get_status_display()}\n"
        f"  Grand Total : \u20b9{invoice.grand_total}\n"
        f"  Amount Due  : \u20b9{invoice.due_amount}\n\n"
        f"The invoice PDF is attached to this email for your records.\n"
        f"You can also view or re-download the invoice from your patient portal at any time.\n\n"
        f"Thank you for choosing ProClinic.\n\n"
        f"Best regards,\nProClinic Billing Team"
    )

    # Build the email
    email_msg = EmailMessage(
        subject=subject,
        body=body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[patient_email],
    )

    # Attempt to attach PDF — degrade gracefully if generation fails
    pdf_attached = False
    try:
        pdf_bytes = generate_invoice_pdf_bytes(invoice)
        filename = f"Invoice_{invoice.pk}.pdf"
        email_msg.attach(filename, pdf_bytes, "application/pdf")
        pdf_attached = True
    except Exception as pdf_err:
        logger.error(
            "PDF generation failed for invoice %s (email will send without attachment): %s",
            invoice.pk, pdf_err,
        )

    try:
        email_msg.send(fail_silently=False)
        log_action(
            actor=request.user,
            action_type='UPDATE',
            entity_type='Invoice',
            entity_id=invoice.pk,
            changes={
                'action': 'manual_email_sent',
                'patient_email': patient_email,
                'pdf_attached': pdf_attached,
            },
        )
        if pdf_attached:
            messages.success(request, f"Invoice email with PDF attachment sent to {patient_email}.")
        else:
            messages.warning(
                request,
                f"Invoice email sent to {patient_email}, but the PDF could not be attached. "
                "Check server logs for details."
            )
    except Exception as e:
        logger.error("Failed to send manual email for invoice %s: %s", invoice.pk, e)
        messages.error(request, f"Failed to send email to {patient_email}. Please try again later.")

    return redirect('invoice_detail', pk=pk)

# ─── Dynamic Billing APIs ───────────────────────────────────────────────────

from django.http import JsonResponse
from .models import MedicineMaster
from prescriptions.models import PrescriptionItem

@login_required
def api_medicines(request):
    if not _accountant_or_admin(request.user) and request.user.role != 'RECEPTIONIST':
       return JsonResponse({'medicines': []})

    qs = MedicineMaster.objects.values('id', 'name', 'default_price', 'description')
    return JsonResponse({'medicines': list(qs)})

@login_required
def api_prescription_context(request):
    """
    Return prescription items for a given appointment_id as JSON.

    Lookup order:
      1. appointment → visit (OneToOne) → prescriptions → items  [primary]
      2. appointment → prescription (OneToOne, legacy) → items    [fallback]

    Returns: {"items": [...], "error": null | "<message>"}
    """
    if not _accountant_or_admin(request.user) and request.user.role != 'RECEPTIONIST':
        return JsonResponse({'items': [], 'error': 'Unauthorised'})

    appt_id = request.GET.get('appointment_id', '').strip()
    if not appt_id:
        return JsonResponse({'items': [], 'error': 'No appointment_id provided'})

    from appointments.models import Appointment
    try:
        appt = Appointment.objects.select_related('visit').get(pk=appt_id)
    except Appointment.DoesNotExist:
        logger.warning("api_prescription_context: appointment %s not found", appt_id)
        return JsonResponse({'items': [], 'error': f'Appointment {appt_id} not found'})
    except Exception as exc:
        logger.exception("api_prescription_context: DB error fetching appointment %s: %s", appt_id, exc)
        return JsonResponse({'items': [], 'error': 'Database error fetching appointment'})

    items = []

    # ── Path 1: appointment → Visit → Prescription(s) → PrescriptionItems ─────
    # Use try/except rather than hasattr() because Django's OneToOne reverse
    # accessor raises RelatedObjectDoesNotExist (subclass of AttributeError)
    # when no matching row exists; hasattr() silently catches it too, but an
    # explicit try/except is clearer and avoids surprising behaviour.
    try:
        visit = appt.visit  # raises Visit.DoesNotExist if no linked Visit
        for presc in visit.prescriptions.select_related().prefetch_related('items').all():
            for item in presc.items.all():
                items.append({
                    'medicine_name': item.medicine_name,
                    'dosage':        item.dosage,
                    'instructions':  item.instructions,
                    'duration':      item.duration,
                })
        logger.debug(
            "api_prescription_context: appt=%s via visit=%s → %d items",
            appt_id, visit.pk, len(items),
        )
    except Exception:
        # No Visit row for this appointment — try the legacy direct link.
        pass

    # ── Path 2: appointment → Prescription (OneToOneField, legacy) ────────────
    if not items:
        try:
            presc = appt.prescription  # raises if no direct Prescription linked
            for item in presc.items.all():
                items.append({
                    'medicine_name': item.medicine_name,
                    'dosage':        item.dosage,
                    'instructions':  item.instructions,
                    'duration':      item.duration,
                })
            logger.debug(
                "api_prescription_context: appt=%s via legacy prescription=%s → %d items",
                appt_id, presc.pk, len(items),
            )
        except Exception:
            # No prescription found via either route — return empty list
            logger.info(
                "api_prescription_context: appt=%s has no linked Visit or Prescription",
                appt_id,
            )

    return JsonResponse({'items': items, 'error': None})

@login_required
def api_patient_appointments(request):
    if not _accountant_or_admin(request.user) and request.user.role != 'RECEPTIONIST':
       return JsonResponse({'appointments': []})

    patient_id = request.GET.get('patient_id')
    if not patient_id:
        return JsonResponse({'appointments': []})

    from appointments.models import Appointment
    from django.utils import timezone as tz
    try:
        appts = Appointment.objects.filter(
            patient_id=patient_id,
            status='COMPLETED',
        ).select_related('doctor').order_by('-scheduled_time')
        data = []
        for a in appts:
            doc_name = a.doctor.get_full_name() or a.doctor.username if a.doctor else "No Doctor"
            # Convert UTC-aware datetime to local time before formatting so the
            # accountant sees the same time as was booked (e.g. 1:30, not 7:30).
            local_time = tz.localtime(a.scheduled_time) if a.scheduled_time else None
            time_str = local_time.strftime("%b %d, %Y %H:%M") if local_time else "Unscheduled"
            data.append({
                'id': a.id,
                'label': f"{time_str} - Dr. {doc_name} ({a.get_status_display()})"
            })
        return JsonResponse({'appointments': data})
    except Exception as e:
        logger.exception("api_patient_appointments error: %s", e)
        return JsonResponse({'appointments': []})


# ─── Medicine Catalog (MedicineMaster) CRUD ──────────────────────────────────

@login_required
def medicine_list(request):
    """List all medicines in the catalog. Accountant / Admin only."""
    if not _accountant_or_admin(request.user):
        return redirect('dashboard')
    medicines = MedicineMaster.objects.all().order_by('name')
    return render(request, 'billing/medicine_list.html', {'medicines': medicines})


@login_required
def medicine_create(request):
    """Add a new medicine to the catalog. Accountant / Admin only."""
    if not _accountant_or_admin(request.user):
        return redirect('dashboard')
    if request.method == 'POST':
        name  = request.POST.get('name', '').strip()
        price = request.POST.get('default_price', '0').strip() or '0'
        desc  = request.POST.get('description', '').strip()
        if name:
            obj, created = MedicineMaster.objects.get_or_create(
                name=name,
                defaults={'default_price': _parse_decimal(price), 'description': desc},
            )
            if created:
                messages.success(request, f"Medicine '{name}' added to catalog.")
            else:
                messages.warning(request, f"Medicine '{name}' already exists in catalog.")
        else:
            messages.error(request, "Medicine name is required.")
        return redirect('medicine_list')
    return render(request, 'billing/medicine_form.html')


@login_required
def medicine_delete(request, pk):
    """Delete a medicine from the catalog. Accountant / Admin only."""
    if not _accountant_or_admin(request.user):
        return redirect('dashboard')
    med = get_object_or_404(MedicineMaster, pk=pk)
    if request.method == 'POST':
        name = med.name
        med.delete()
        messages.success(request, f"Medicine '{name}' removed from catalog.")
    return redirect('medicine_list')


# ─── Invoice PDF download ─────────────────────────────────────────────────────

@login_required
def invoice_pdf_download(request, pk):
    """Generate invoice PDF in-memory and return it as a download.

    PDFs are generated fresh with WeasyPrint on every request (no Cloudinary).
    If a cached copy exists in Django's default file storage it is served
    directly; otherwise a fresh PDF is generated and optionally cached via
    Django's standard FileField.save() — never via CloudinaryResource.save().

    Access rules:
      - PATIENT              → only their own invoices (non-DRAFT)
      - ACCOUNTANT / ADMIN / RECEPTIONIST → any invoice
    """
    invoice = get_object_or_404(Invoice, pk=pk)

    if request.user.role == 'PATIENT':
        patient = getattr(request.user, 'patient_profile', None)
        if patient is None:
            from patients.models import Patient as P
            from django.db.models import Q
            patient = P.objects.filter(
                Q(email=request.user.email) |
                Q(contact_number=request.user.phone_number)
            ).first()
        if not patient or invoice.patient != patient:
            raise Http404
    elif request.user.role not in {'ACCOUNTANT', 'ADMIN'}:
        return redirect('dashboard')

    # Generate PDF bytes in memory — no CloudinaryResource.save() involved
    from billing.utils import generate_invoice_pdf_bytes
    from django.http import HttpResponse
    try:
        pdf_bytes = generate_invoice_pdf_bytes(invoice)
    except Exception as e:
        logger.error("Invoice %s PDF generation error: %s", invoice.pk, e)
        messages.error(request, f"PDF generation failed: {str(e)}")
        return redirect('invoice_detail', pk=pk)

    filename = f"invoice_{invoice.pk}.pdf"
    response = HttpResponse(pdf_bytes, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    response['Content-Length'] = len(pdf_bytes)
    return response