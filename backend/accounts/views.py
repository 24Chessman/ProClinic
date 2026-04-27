from django.contrib.auth import login, update_session_auth_hash
from django.contrib.auth.views import LoginView
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from django.shortcuts import redirect, render, get_object_or_404
from django.views.decorators.http import require_POST
import logging

from .forms import (
    StaffProfileForm,
    PatientPasswordChangeForm,
    PatientProfileForm,
    PatientSignUpForm,
    StaffCreationForm,
)
from patients.models import Patient
from audit.models import AuditLog
from .models import CustomUser

logger = logging.getLogger(__name__)


STAFF_ROLES = {'ADMIN', 'DOCTOR', 'RECEPTIONIST', 'PHARMACIST', 'ACCOUNTANT'}


def choose_login(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    return render(request, 'accounts/choose_login.html')


class RoleBasedLoginView(LoginView):
    redirect_authenticated_user = True
    allowed_roles = set()
    portal_label = ''

    def form_valid(self, form):
        user = form.get_user()
        if user.role not in self.allowed_roles:
            form.add_error(
                None,
                f"This account is not authorized for the {self.portal_label} portal.",
            )
            return self.form_invalid(form)
        response = super().form_valid(form)
        
        AuditLog.objects.create(
            actor=user,
            action_type='LOGIN',
            entity_type='CustomUser',
            entity_id=user.pk,
            changes={'ip': self.request.META.get('REMOTE_ADDR', 'unknown')},
        )
        
        return response


class StaffLoginView(RoleBasedLoginView):
    template_name = 'accounts/staff_login.html'
    allowed_roles = STAFF_ROLES
    portal_label = 'Staff'


class PatientLoginView(RoleBasedLoginView):
    template_name = 'accounts/patient_login.html'
    allowed_roles = {'PATIENT'}
    portal_label = 'Patient'


def patient_signup(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        form = PatientSignUpForm(request.POST)
        if form.is_valid():
            try:
                with transaction.atomic():
                    user = form.save(commit=False)
                    user.role = 'PATIENT'
                    user.phone_number = form.cleaned_data.get('phone_number')
                    user.save()
                    Patient.objects.create(
                        user=user,
                        first_name=form.cleaned_data['first_name'],
                        last_name=form.cleaned_data['last_name'],
                        date_of_birth=form.cleaned_data['date_of_birth'],
                        gender=form.cleaned_data['gender'],
                        blood_group=form.cleaned_data['blood_group'],
                        contact_number=form.cleaned_data['phone_number'],
                        email=form.cleaned_data['email'],
                        address=form.cleaned_data['address'],
                        allergies=form.cleaned_data.get('allergies', ''),
                    )
                login(request, user)
                return redirect('dashboard')
            except Exception as exc:
                logger.exception('patient_signup: unexpected error during account creation')
                messages.error(
                    request,
                    'An unexpected error occurred while creating your account. Please try again.'
                )
    else:
        form = PatientSignUpForm()

    return render(request, 'accounts/patient_signup.html', {'form': form})


@login_required
def create_staff_account(request):
    if request.user.role != 'ADMIN':
        return redirect('dashboard')

    if request.method == 'POST':
        form = StaffCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            messages.success(
                request,
                f"Staff account created for {user.username} ({user.get_role_display()}).",
            )
            return redirect('create_staff_account')
    else:
        form = StaffCreationForm()

    staff_list = CustomUser.objects.exclude(role='PATIENT').order_by('-is_active', '-date_joined')
    return render(request, 'accounts/create_staff_account.html', {'form': form, 'staff_list': staff_list})

@require_POST
@login_required
def deactivate_staff_account(request, pk):
    if request.user.role != 'ADMIN':
        return redirect('dashboard')

    target_user = get_object_or_404(CustomUser, pk=pk)

    if target_user.role == 'PATIENT':
        messages.error(request, "Cannot deactivate patient accounts from this portal.")
        return redirect('create_staff_account')

    if target_user == request.user:
        messages.error(request, "Safety block: You cannot deactivate your own account.")
        return redirect('create_staff_account')

    if target_user.role == 'ADMIN' and target_user.is_active:
        active_admins = CustomUser.objects.filter(role='ADMIN', is_active=True).count()
        if active_admins <= 1:
            messages.error(request, "Safety block: Cannot deactivate the last active administrator account.")
            return redirect('create_staff_account')

    target_user.is_active = False
    target_user.save(update_fields=['is_active'])
    
    AuditLog.objects.create(
        actor=request.user,
        action_type='UPDATE',
        entity_type='CustomUser',
        entity_id=target_user.pk,
        changes={'action': 'deactivated account', 'target': target_user.username},
    )
    
    messages.success(request, f"Staff account {target_user.username} deactivated successfully.")
    return redirect('create_staff_account')


@require_POST
@login_required
def reactivate_staff_account(request, pk):
    """POST – reactivate a deactivated staff account. Admin only."""
    if request.user.role != 'ADMIN':
        return redirect('dashboard')

    target_user = get_object_or_404(CustomUser, pk=pk)

    if target_user.role == 'PATIENT':
        messages.error(request, "Cannot reactivate patient accounts from this portal.")
        return redirect('create_staff_account')

    if target_user.is_active:
        messages.info(request, f"Account {target_user.username} is already active.")
        return redirect('create_staff_account')

    target_user.is_active = True
    target_user.save(update_fields=['is_active'])

    AuditLog.objects.create(
        actor=request.user,
        action_type='UPDATE',
        entity_type='CustomUser',
        entity_id=target_user.pk,
        changes={'action': 'reactivated account', 'target': target_user.username},
    )

    messages.success(request, f"Staff account {target_user.username} reactivated successfully.")
    return redirect('create_staff_account')


@login_required
def patient_profile(request):
    if request.user.role != 'PATIENT':
        return redirect('dashboard')

    # Direct FK lookup first, then legacy email/phone fallback
    profile = getattr(request.user, 'patient_profile', None)
    if profile is None:
        profile = Patient.objects.filter(
            Q(email=request.user.email)
            | Q(contact_number=request.user.phone_number)
            | Q(contact_number=request.user.username)
        ).first()
        # Repair FK for future lookups
        if profile and profile.user_id is None:
            profile.user = request.user
            profile.save(update_fields=['user'])

    initial_profile_data = {}
    if not profile:
        initial_profile_data = {
            'first_name': request.user.first_name,
            'last_name': request.user.last_name,
            'email': request.user.email,
            'contact_number': request.user.phone_number,
        }

    if request.method == 'POST' and request.POST.get('form_type') == 'password':
        profile_form = PatientProfileForm(
            instance=profile,
            initial=initial_profile_data,
        )
        password_form = PatientPasswordChangeForm(request.user, request.POST)
        if password_form.is_valid():
            updated_user = password_form.save()
            update_session_auth_hash(request, updated_user)
            messages.success(request, "Password updated successfully.")
            return redirect('patient_profile')
    elif request.method == 'POST':
        profile_form = PatientProfileForm(
            request.POST,
            instance=profile,
            initial=initial_profile_data,
        )
        password_form = PatientPasswordChangeForm(request.user)
        if profile_form.is_valid():
            with transaction.atomic():
                saved_profile = profile_form.save()
                request.user.first_name = saved_profile.first_name
                request.user.last_name = saved_profile.last_name
                request.user.email = saved_profile.email
                request.user.phone_number = saved_profile.contact_number
                request.user.save(
                    update_fields=['first_name', 'last_name', 'email', 'phone_number']
                )

            messages.success(request, "Profile updated successfully.")
            return redirect('patient_profile')
    else:
        profile_form = PatientProfileForm(
            instance=profile,
            initial=initial_profile_data,
        )
        password_form = PatientPasswordChangeForm(request.user)

    context = {
        'profile_form': profile_form,
        'password_form': password_form,
    }
    return render(request, 'accounts/patient_profile.html', context)


@login_required
def staff_profile(request):
    if request.user.role in {'PATIENT'}:
        return redirect('dashboard')

    if request.method == 'POST':
        form = StaffProfileForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Profile updated successfully.")
            return redirect('staff_profile')
    else:
        form = StaffProfileForm(instance=request.user)
        
    return render(request, 'accounts/staff_profile.html', {'form': form})


# ── Patient Forgot Password Flow ───────────────────────────────────────────────

from django.core.mail import send_mail
from django.conf import settings
from django.contrib.auth.forms import SetPasswordForm
from .models import PatientOTP
from django.utils import timezone
from datetime import timedelta

def patient_forgot_password_request(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    
    if request.method == 'POST':
        identifier = request.POST.get('identifier', '').strip()
        
        # Non-enumerating response setup
        success_msg = "If an account matches that identifier, an OTP has been sent to your registered email."
        
        user = CustomUser.objects.filter(
            Q(username=identifier) | Q(email=identifier),
            role='PATIENT',
            is_active=True
        ).first()

        if user and user.email:
            # Check cooldown (e.g. 2 minutes)
            recent_otp = PatientOTP.objects.filter(user=user).order_by('-created_at').first()
            if recent_otp and (timezone.now() - recent_otp.created_at) < timedelta(minutes=2):
                # Don't say "wait 2 mins", just show success message to prevent enumeration 
                # but actually don't send another email. Or we can show the cooldown message
                # since they already know the identifier is valid if we do. 
                # To be strictly non-enumerating, we just act like it worked.
                pass
            else:
                otp = PatientOTP.generate(user)
                
                subject = "Your ProClinic Password Reset OTP"
                message = f"Hello {user.first_name or user.username},\n\nYour password reset OTP is: {otp.otp_code}\n\nThis OTP will expire in 10 minutes.\nIf you did not request this, please ignore this email.\n\nProClinic Team"
                
                try:
                    send_mail(
                        subject, message, settings.DEFAULT_FROM_EMAIL, [user.email], fail_silently=False
                    )
                except Exception as e:
                    logger.error("Failed to send OTP to %s: %s", user.email, e)

        # Always store the identifier in session so verify step knows who is trying
        # We store it even if invalid, to keep it non-enumerating
        request.session['reset_identifier'] = identifier
        messages.success(request, success_msg)
        return redirect('patient_forgot_password_verify')

    return render(request, 'accounts/forgot_password_request.html')


def patient_forgot_password_verify(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
        
    identifier = request.session.get('reset_identifier')
    if not identifier:
        return redirect('patient_forgot_password_request')

    if request.method == 'POST':
        otp_code = request.POST.get('otp', '').strip()
        
        user = CustomUser.objects.filter(
            Q(username=identifier) | Q(email=identifier),
            role='PATIENT',
            is_active=True
        ).first()
        
        if user:
            otp_obj = PatientOTP.objects.filter(user=user, otp_code=otp_code).order_by('-created_at').first()
            if otp_obj and otp_obj.is_valid():
                # Mark used immediately
                otp_obj.is_used = True
                otp_obj.save()
                
                request.session['can_reset_password'] = True
                request.session['reset_user_id'] = user.id
                messages.success(request, "OTP verified successfully. Please enter your new password.")
                return redirect('patient_forgot_password_reset')
        
        # Invalid or expired
        messages.error(request, "Invalid or expired OTP.")
        
    return render(request, 'accounts/forgot_password_verify.html', {'identifier': identifier})


def patient_forgot_password_reset(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
        
    if not request.session.get('can_reset_password'):
        return redirect('patient_forgot_password_request')
        
    user_id = request.session.get('reset_user_id')
    user = get_object_or_404(CustomUser, id=user_id, role='PATIENT')

    if request.method == 'POST':
        form = SetPasswordForm(user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            
            # Clear session vars
            request.session.pop('reset_identifier', None)
            request.session.pop('can_reset_password', None)
            request.session.pop('reset_user_id', None)
            
            # Log them in
            login(request, user)
            
            AuditLog.objects.create(
                actor=user,
                action_type='UPDATE',
                entity_type='CustomUser',
                entity_id=user.pk,
                changes={'action': 'password_reset_via_otp'},
            )
            
            messages.success(request, "Your password has been successfully reset.")
            return redirect('dashboard')
    else:
        form = SetPasswordForm(user)

    return render(request, 'accounts/forgot_password_reset.html', {'form': form})

