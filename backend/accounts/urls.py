from django.contrib.auth.views import LogoutView
from django.urls import path

from .views import (
    PatientLoginView,
    StaffLoginView,
    choose_login,
    create_staff_account,
    staff_profile,
    patient_profile,
    patient_signup,
    deactivate_staff_account,
    reactivate_staff_account,
    patient_forgot_password_request,
    patient_forgot_password_verify,
    patient_forgot_password_reset,
)


urlpatterns = [
    path('choose-login/', choose_login, name='choose_login'),
    path('login/staff/', StaffLoginView.as_view(), name='staff_login'),
    path('login/patient/', PatientLoginView.as_view(), name='patient_login'),
    path('signup/patient/', patient_signup, name='patient_signup'),
    path('profile/patient/', patient_profile, name='patient_profile'),
    path('profile/staff/', staff_profile, name='staff_profile'),
    path('staff/create/', create_staff_account, name='create_staff_account'),
    path('staff/deactivate/<int:pk>/', deactivate_staff_account, name='deactivate_staff'),
    path('staff/reactivate/<int:pk>/', reactivate_staff_account, name='reactivate_staff'),
    path('logout/', LogoutView.as_view(), name='logout'),
    
    # Patient forgot password
    path('login/patient/forgot-password/', patient_forgot_password_request, name='patient_forgot_password_request'),
    path('login/patient/forgot-password/verify/', patient_forgot_password_verify, name='patient_forgot_password_verify'),
    path('login/patient/forgot-password/reset/', patient_forgot_password_reset, name='patient_forgot_password_reset'),
]
