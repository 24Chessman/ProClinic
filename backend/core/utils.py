from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)

def send_appointment_notification(appointment, action='created'):
    """
    Send a professional email notification for appointment events.

    action: 'created' | 'rescheduled' | 'cancelled'

    Booking must never fail due to email issues — all exceptions are caught and logged.
    """
    if not appointment.patient.email:
        logger.warning(
            "No email on record for patient %s — skipping appointment notification.",
            appointment.patient.first_name,
        )
        return False

    doctor_name = f"Dr. {appointment.doctor.get_full_name() or appointment.doctor.username}"
    patient_name = appointment.patient.first_name
    local_time   = timezone.localtime(appointment.scheduled_time)
    date_str     = local_time.strftime('%A, %d %B %Y')
    time_str     = local_time.strftime('%I:%M %p')
    status_str   = appointment.get_status_display() if hasattr(appointment, 'get_status_display') else appointment.status

    if action == 'created':
        subject = "Appointment Confirmed — ProClinic"
        body = (
            f"Dear {patient_name},\n\n"
            f"Your appointment has been successfully booked at ProClinic. Here are your details:\n\n"
            f"  Doctor      : {doctor_name}\n"
            f"  Date        : {date_str}\n"
            f"  Time        : {time_str}\n"
            f"  Status      : {status_str}\n"
        )
        if hasattr(appointment, 'reason') and appointment.reason:
            body += f"  Reason      : {appointment.reason}\n"
        body += (
            f"\nPlease arrive 10 minutes early and bring any relevant medical records.\n"
            f"You can view or cancel your appointment from the Patient Portal.\n\n"
            f"Thank you for choosing ProClinic. We look forward to seeing you.\n\n"
            f"Warm regards,\nProClinic Team"
        )

    elif action == 'rescheduled':
        subject = "Appointment Rescheduled — ProClinic"
        body = (
            f"Dear {patient_name},\n\n"
            f"Your appointment has been rescheduled. Updated details below:\n\n"
            f"  Doctor      : {doctor_name}\n"
            f"  New Date    : {date_str}\n"
            f"  New Time    : {time_str}\n"
            f"  Status      : {status_str}\n\n"
            f"If you did not request this change, please contact the clinic immediately.\n\n"
            f"Thank you,\nProClinic Team"
        )

    elif action == 'cancelled':
        subject = "Appointment Cancelled — ProClinic"
        body = (
            f"Dear {patient_name},\n\n"
            f"Your appointment with {doctor_name} on {date_str} at {time_str} has been cancelled.\n\n"
            f"If you need to rebook, please visit the Patient Portal or contact reception.\n\n"
            f"Thank you,\nProClinic Team"
        )

    else:
        subject = f"Appointment Update — ProClinic"
        body = (
            f"Dear {patient_name},\n\n"
            f"Your appointment with {doctor_name} on {date_str} at {time_str} has been updated "
            f"(status: {status_str}).\n\n"
            f"Thank you,\nProClinic Team"
        )

    try:
        sender_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@proclinic.local')
        send_mail(
            subject=subject,
            message=body,
            from_email=sender_email,
            recipient_list=[appointment.patient.email],
            fail_silently=True,   # booking must never crash due to email
        )
        logger.info(
            "Appointment %s notification (%s) sent to %s.",
            appointment.pk, action, appointment.patient.email,
        )
        return True
    except Exception as e:
        logger.error("Failed to send appointment %s email for appt %s: %s", action, appointment.pk, e)
        return False



def send_lab_report_notification(report, patient_profile):
    """
    Notify every doctor who has an appointment record with this patient
    that they have uploaded a new lab report requiring review.

    Uses the same fail-silent email approach as send_appointment_notification.
    Never raises — any errors are logged only.
    """
    from appointments.models import Appointment

    doctor_emails = (
        Appointment.objects
        .filter(patient=patient_profile)
        .exclude(doctor__email='')
        .exclude(doctor__email__isnull=True)
        .values_list('doctor__email', 'doctor__first_name', 'doctor__last_name')
        .distinct()
    )

    if not doctor_emails:
        logger.info(
            "Lab report %s uploaded; no doctor emails found for patient %s.",
            report.pk,
            patient_profile,
        )
        return

    patient_name = f"{patient_profile.first_name} {patient_profile.last_name}".strip()
    subject = f"New Lab Report Uploaded — {patient_name} | ProClinic"
    sender_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@proclinic.local')

    for email, first, last in doctor_emails:
        doctor_name = f"Dr. {first} {last}".strip()
        message = (
            f"Dear {doctor_name},\n\n"
            f"Your patient {patient_name} has uploaded a new lab report for your review:\n\n"
            f"  Test / Report:  {report.test_name}\n"
            f"  Test Date:      {report.report_date}\n"
            f"  Status:         Pending Review\n\n"
            "Please log in to ProClinic to review and verify the report.\n\n"
            "Thank you,\nProClinic System"
        )
        try:
            send_mail(
                subject=subject,
                message=message,
                from_email=sender_email,
                recipient_list=[email],
                fail_silently=True,
            )
            logger.info("Lab report notification sent to %s for report %s.", email, report.pk)
        except Exception as exc:
            logger.error("Failed to send lab report notification to %s: %s", email, exc)
