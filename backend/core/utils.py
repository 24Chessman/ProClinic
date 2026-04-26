from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)

def send_appointment_notification(appointment, action='created'):
    """
    Send an email notification for appointment events (created, rescheduled, cancelled).
    Since email backend might not be configured in development, we catch exceptions.
    """
    if not appointment.patient.email:
        logger.warning(f"No email for patient {appointment.patient.first_name}, skipping notification.")
        return False
        
    subject = f"Appointment {action.capitalize()} - ProClinic"
    
    date_str = appointment.scheduled_time.strftime('%Y-%m-%d %H:%M')
    message = (
        f"Dear {appointment.patient.first_name},\n\n"
        f"Your appointment has been {action}.\n"
        f"Doctor: Dr. {appointment.doctor.get_full_name()}\n"
        f"Time: {date_str}\n\n"
        "Thank you,\nProClinic Team"
    )
    
    try:
        sender_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@proclinic.local')
        send_mail(
            subject=subject,
            message=message,
            from_email=sender_email,
            recipient_list=[appointment.patient.email],
            fail_silently=True
        )
        return True
    except Exception as e:
        logger.error(f"Failed to send email: {e}")
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
