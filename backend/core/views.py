from datetime import timedelta
from decimal import Decimal

from django.db.models import Q, Sum
from django.shortcuts import redirect, render
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.conf import settings
from accounts.models import CustomUser
from audit.models import AuditLog
from billing.models import Invoice
from patients.models import Patient, Visit, LabReport
from appointments.models import Appointment
from publications.models import Publication
from prescriptions.models import Prescription, PrescriptionItem


def home(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    return redirect('choose_login')


def design_system(request):
    return render(request, 'prototype/design_system.html')


def prototype_prescription_a4(request):
    return render(
        request,
        'prototype/prescription_a4.html',
        {'today': timezone.localdate()},
    )


def prototype_invoice_a4(request):
    return render(
        request,
        'prototype/invoice_a4.html',
        {'today': timezone.localdate()},
    )


def permission_error(request):
    return render(request, 'prototype/permission_error.html', status=403)


@login_required
def dashboard(request):
    user = request.user
    now = timezone.now()
    today = now.date()
    week_ago = now - timedelta(days=7)

    context = {
        'role': user.role,
        'today': today,
    }

    if user.role == 'ADMIN':
        context.update({
            'total_staff': CustomUser.objects.exclude(role='PATIENT').count(),
            'total_patients': Patient.objects.count(),
            'today_appointments': Appointment.objects.filter(scheduled_time__date=today).count(),
            'daily_logins': AuditLog.objects.filter(action_type='LOGIN', timestamp__date=today).count(),
            'pending_papers': Publication.objects.filter(status='PENDING').count(),
            'audit_feed': AuditLog.objects.order_by('-timestamp')[:8],
            'deletion_logs': AuditLog.objects.filter(action_type='DELETE').order_by('-timestamp')[:5],
            'support_queue': Appointment.objects.filter(status__in=['CANCELLED', 'NOSHOW']).count(),
        })

    elif user.role == 'DOCTOR':
        context.update({
            'upcoming_appointments': Appointment.objects.filter(
                doctor=user,
                status='SCHEDULED',
                scheduled_time__gte=now,
            ).select_related('patient').order_by('scheduled_time')[:8],
            'my_patient_count': Patient.objects.filter(
                appointments__doctor=user,
                appointments__status__in=['SCHEDULED', 'RESCHEDULED', 'COMPLETED', 'CHECKED_IN']
            ).distinct().count(),
            'my_prescription_count': Prescription.objects.filter(doctor=user).count(),
            'my_pending_research': Publication.objects.filter(doctor=user, status='PENDING').count(),
            'ehr_records_count': Visit.objects.filter(doctor=user).count(),
            'my_recent_visits': Appointment.objects.filter(
                doctor=user
            ).select_related('patient').order_by('-scheduled_time')[:6],
        })

    elif user.role == 'RECEPTIONIST':
        context.update({
            'today_bookings': Appointment.objects.filter(
                scheduled_time__date=today,
            ).count(),
            'total_today_slots': Appointment.objects.filter(
                status__in=['SCHEDULED', 'RESCHEDULED'],
                scheduled_time__date=today,
            ).count(),
            'new_patient_registrations': Patient.objects.filter(created_at__gte=week_ago).count(),
            'pending_reschedules': Appointment.objects.filter(status='RESCHEDULED').count(),
            'walk_in_followups': Appointment.objects.filter(
                status__in=['SCHEDULED', 'RESCHEDULED'],
                scheduled_time__date=today,
            ).select_related('patient', 'doctor').order_by('scheduled_time')[:12],
        })


    elif user.role == 'ACCOUNTANT':
        paid_total    = Invoice.objects.filter(status='PAID').aggregate(total=Sum('total_amount'))['total'] or Decimal('0')
        pending_total = Invoice.objects.filter(status__in=['UNPAID', 'PARTIAL']).aggregate(total=Sum('total_amount'))['total'] or Decimal('0')
        draft_invoices = Invoice.objects.filter(status='DRAFT').select_related('patient', 'appointment').order_by('-created_at')
        draft_count    = draft_invoices.count()
        context.update({
            'paid_total':    paid_total,
            'pending_total': pending_total,
            'gst_estimate':  (paid_total * Decimal(str(settings.GST_RATE))).quantize(Decimal('0.01')),
            'unpaid_invoices': Invoice.objects.filter(status='UNPAID').count(),
            'counts': {
                'PAID':    Invoice.objects.filter(status='PAID').count(),
                'PARTIAL': Invoice.objects.filter(status='PARTIAL').count(),
                'UNPAID':  Invoice.objects.filter(status='UNPAID').count(),
            },
            'recent_invoices': Invoice.objects.select_related('patient').order_by('-updated_at')[:10],
            'draft_invoices': draft_invoices[:8],
            'draft_count':   draft_count,
        })


    elif user.role == 'PHARMACIST':
        pending_qs = Prescription.objects.filter(dispense_status='PENDING')
        context.update({
            'today_prescriptions': Prescription.objects.filter(created_at__date=today).count(),
            'total_medicine_lines': PrescriptionItem.objects.filter(
                prescription__created_at__date=today
            ).count(),
            'dispense_queue': pending_qs.select_related('patient', 'doctor').prefetch_related('items').order_by('-created_at')[:10],
            'pending_count': pending_qs.count(),
            'dispensed_today': Prescription.objects.filter(
                dispense_status='DISPENSED',
                dispensed_at__date=today,
            ).count(),
            'recent_prescriptions': Prescription.objects.select_related('patient', 'doctor').order_by('-created_at')[:8],
        })


    elif user.role == 'PATIENT':
        from patients.utils import get_patient_profile
        patient_profile = get_patient_profile(user)

        my_history = Appointment.objects.none()
        my_past_history = Appointment.objects.none()
        my_upcoming_appointments = Appointment.objects.none()
        my_prescriptions = Prescription.objects.none()
        my_invoices = Invoice.objects.none()
        if patient_profile:
            my_history = Appointment.objects.filter(patient=patient_profile).select_related('doctor').order_by('-scheduled_time')
            my_past_history = my_history.filter(scheduled_time__lt=now).order_by('-scheduled_time')
            my_upcoming_appointments = my_history.filter(
                scheduled_time__gte=now,
                status='SCHEDULED',
            ).order_by('scheduled_time')
            my_prescriptions = Prescription.objects.filter(patient=patient_profile).select_related('doctor').order_by('-created_at')
            my_invoices = Invoice.objects.filter(patient=patient_profile).order_by('-updated_at')

        context.update({
            'patient_profile': patient_profile,
            'my_past_history': my_past_history[:10],
            'my_upcoming_appointments': my_upcoming_appointments[:10],
            'my_prescriptions': my_prescriptions[:10],
            'my_total_visits': my_history.count(),
            'my_invoice_due': my_invoices.filter(status__in=['UNPAID', 'PARTIAL']).aggregate(total=Sum('total_amount'))['total'] or 0,
            'my_lab_reports_count': LabReport.objects.filter(patient=patient_profile).count() if patient_profile else 0,
        })

    return render(request, 'dashboard.html', context)
