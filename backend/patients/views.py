from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, viewsets
from rest_framework.permissions import IsAuthenticated

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render

from api.filters import PatientFilter
from api.pagination import StandardResultsSetPagination
from api.permissions import IsStaff

from django.contrib.auth import get_user_model

from .models import LabReport, Patient, Visit
from .serializers import PatientSerializer


class PatientViewSet(viewsets.ModelViewSet):
    """
    Staff-facing patient management.

    Filtering:  ?first_name=  ?last_name=  ?blood_group=  ?gender=
    Search:     ?search=  (first_name, last_name, contact_number, email)
    Ordering:   ?ordering=first_name | last_name | created_at
    Pagination: ?page=  ?page_size=  (default 20, max 100)
    """
    queryset = Patient.objects.all().order_by('last_name', 'first_name')
    serializer_class = PatientSerializer
    permission_classes = [IsAuthenticated, IsStaff]
    pagination_class = StandardResultsSetPagination

    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = PatientFilter
    search_fields = ['first_name', 'last_name', 'contact_number', 'email']
    ordering_fields = ['first_name', 'last_name', 'created_at']
    ordering = ['last_name', 'first_name']


@login_required
def patient_list(request):
    from django.core.paginator import Paginator
    if request.user.role not in {'ADMIN', 'RECEPTIONIST'}:
        return redirect('dashboard')
        
    User = get_user_model()
    q = request.GET.get('q', '').strip()
    
    # Base queries
    patients = Patient.objects.all().order_by('first_name', 'last_name')
    staff = User.objects.exclude(role='PATIENT').order_by('first_name', 'last_name')
    
    if q:
        patients = patients.filter(
            Q(first_name__icontains=q) | 
            Q(last_name__icontains=q) | 
            Q(contact_number__icontains=q) | 
            Q(email__icontains=q)
        )
        staff = staff.filter(
            Q(first_name__icontains=q) | 
            Q(last_name__icontains=q) | 
            Q(username__icontains=q) |
            Q(email__icontains=q)
        )
        
    paginator = Paginator(patients, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
        
    context = {
        'patients': page_obj,
        'doctors': staff.filter(role='DOCTOR'),
        'receptionists': staff.filter(role='RECEPTIONIST'),
        'pharmacists': staff.filter(role='PHARMACIST'),
        'accountants': staff.filter(role='ACCOUNTANT'),
        'admins': staff.filter(role='ADMIN'),
        'search_query': q,
    }
    return render(request, 'patients/patient_list.html', context)

@login_required
def patient_detail(request, pk):
    if request.user.role not in {'ADMIN', 'DOCTOR', 'RECEPTIONIST'}:
        return redirect('dashboard')
    # This function now correctly uses get_object_or_404
    patient = get_object_or_404(Patient, pk=pk)

    if request.user.role == 'DOCTOR':
        has_access = patient.appointments.filter(doctor=request.user).exists()
        if not has_access:
            return redirect('dashboard')
    
    # Fetching related data through Reverse Relations
    appointments = patient.appointments.all().order_by('-scheduled_time')
    prescriptions = patient.prescriptions.all().order_by('-created_at')
    invoices = patient.invoices.all().order_by('-created_at')
    lab_reports = patient.lab_reports.all().order_by('-uploaded_at')
    
    context = {
        'patient': patient,
        'appointments': appointments,
        'prescriptions': prescriptions,
        'invoices': invoices,
        'lab_reports': lab_reports,
    }
    return render(request, 'patients/patient_detail.html', context)

from .forms import PatientForm

@login_required
def patient_create(request):
    if request.user.role not in {'ADMIN', 'RECEPTIONIST'}:
        return redirect('dashboard')
    
    if request.method == 'POST':
        form = PatientForm(request.POST)
        if form.is_valid():
            patient = form.save()
            messages.success(request, "Patient profile created successfully.")
            return redirect('patient_detail', pk=patient.pk)
    else:
        form = PatientForm()
    
    context = {'form': form, 'title': 'Register New Patient'}
    return render(request, 'patients/patient_form.html', context)

@login_required
def patient_update(request, pk):
    if request.user.role not in {'ADMIN', 'RECEPTIONIST'}:
        return redirect('dashboard')
        
    patient = get_object_or_404(Patient, pk=pk)
    
    if request.method == 'POST':
        form = PatientForm(request.POST, instance=patient)
        if form.is_valid():
            form.save()
            messages.success(request, "Patient profile updated successfully.")
            return redirect('patient_detail', pk=patient.pk)
    else:
        form = PatientForm(instance=patient)
    context = {'form': form, 'title': 'Edit Patient Details', 'patient': patient}
    return render(request, 'patients/patient_form.html', context)

@login_required
def lab_report_verify(request, pk):
    # Only DOCTOR and ADMIN may clinically verify a lab report.
    # Receptionists can view but not verify.
    if request.user.role not in {'ADMIN', 'DOCTOR'}:
        messages.error(request, "Only doctors and administrators can verify lab reports.")
        next_url = request.POST.get('next') or request.GET.get('next')
        return redirect(next_url) if next_url else redirect('dashboard')
    report = get_object_or_404(LabReport, pk=pk)
    if request.method == 'POST':
        report.mark_verified(user=request.user)
        messages.success(request, f"Lab report '{report.test_name}' marked as verified.")
    next_url = request.POST.get('next')
    return redirect(next_url) if next_url else redirect('patient_detail', pk=report.patient.pk)

@login_required
def lab_report_archive(request, pk):
    # Archiving is ADMIN-only to prevent accidental clinical data loss.
    if request.user.role not in {'ADMIN'}:
        messages.error(request, "Only administrators can archive lab reports.")
        next_url = request.POST.get('next') or request.GET.get('next')
        return redirect(next_url) if next_url else redirect('dashboard')
    report = get_object_or_404(LabReport, pk=pk)
    if request.method == 'POST':
        report.mark_archived()
        messages.success(request, f"Lab report '{report.test_name}' archived.")
    next_url = request.POST.get('next')
    return redirect(next_url) if next_url else redirect('patient_detail', pk=report.patient.pk)


# ─── Patient Self-Service Views ───────────────────────────────────────────────

from patients.utils import get_patient_profile


@login_required
def patient_my_prescriptions(request):
    """Patient self-service: view own prescription history."""
    if request.user.role != 'PATIENT':
        return redirect('dashboard')

    profile = get_patient_profile(request.user)
    prescriptions = []
    if profile:
        prescriptions = (
            profile.prescriptions
            .select_related('doctor')
            .prefetch_related('items')
            .order_by('-created_at')
        )

    return render(request, 'patients/my_prescriptions.html', {
        'prescriptions': prescriptions,
        'profile': profile,
    })


@login_required
def patient_my_visits(request):
    """Patient self-service: view own clinical visit / EHR history."""
    if request.user.role != 'PATIENT':
        return redirect('dashboard')

    profile = get_patient_profile(request.user)
    visits = []
    if profile:
        visits = (
            Visit.objects.filter(patient=profile)
            .select_related('doctor', 'appointment')
            .order_by('-visit_date')
        )

    return render(request, 'patients/my_visits.html', {
        'visits': visits,
        'profile': profile,
    })


@login_required
def patient_my_lab_reports(request):
    """Patient self-service: list own lab reports and upload a new one."""
    if request.user.role != 'PATIENT':
        return redirect('dashboard')

    profile = get_patient_profile(request.user)
    if not profile:
        messages.warning(request, "Patient profile not found. Please contact reception.")
        return redirect('dashboard')

    if request.method == 'POST':
        test_name = request.POST.get('test_name', '').strip()
        report_date = request.POST.get('report_date', '').strip()
        pdf_file = request.FILES.get('pdf_file')

        errors = []
        if not test_name:
            errors.append("Test name is required.")
        if not report_date:
            errors.append("Report date is required.")
        if not pdf_file:
            errors.append("Please select a PDF file to upload.")
        elif not pdf_file.name.lower().endswith('.pdf'):
            errors.append("Only PDF files are accepted.")
        elif pdf_file.size > 5 * 1024 * 1024:
            errors.append("File must not exceed 5 MB.")

        if errors:
            for err in errors:
                messages.error(request, err)
        else:
            report = LabReport.objects.create(
                patient=profile,
                uploaded_by=request.user,
                test_name=test_name,
                report_date=report_date,
                pdf_file=pdf_file,
            )
            messages.success(request, "Lab report uploaded successfully.")

            # ── Notify doctors who have ever treated this patient ──────────
            from core.utils import send_lab_report_notification
            send_lab_report_notification(report, profile)
            # ─────────────────────────────────────────────────────────────

            return redirect('patient_lab_reports')

    reports = LabReport.objects.filter(patient=profile).order_by('-uploaded_at')
    return render(request, 'patients/my_lab_reports.html', {
        'reports': reports,
        'profile': profile,
    })


@login_required
def patient_cancel_appointment(request, pk):
    from appointments.models import Appointment
    from core.utils import send_appointment_notification
    
    if request.user.role != 'PATIENT':
        return redirect('dashboard')
        
    appointment = get_object_or_404(Appointment, pk=pk, patient__user=request.user)
    
    if request.method == 'POST':
        if appointment.status == 'CHECKED_IN':
            messages.error(request, "Cannot cancel an appointment after you have checked in. Please see the receptionist.")
        elif appointment.is_cancellable:
            appointment.cancel(user=request.user, reason="Patient cancelled via portal")
            send_appointment_notification(appointment, 'cancelled')
            messages.success(request, "Your appointment has been cancelled.")
        else:
            messages.error(request, f"Cannot cancel a {appointment.get_status_display()} appointment.")
            
    return redirect('dashboard')
