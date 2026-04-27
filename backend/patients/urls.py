from django.urls import path
from .views import (
    patient_list,
    patient_detail,
    patient_create,
    patient_update,
    patient_my_prescriptions,
    patient_my_visits,
    patient_my_lab_reports,
    doctor_lab_reports,
    lab_report_verify,
    lab_report_archive,
    patient_cancel_appointment,
    patient_ai_ask,
)

urlpatterns = [
    path('', patient_list, name='patient_list'),
    path('create/', patient_create, name='patient_create'),
    path('<int:pk>/', patient_detail, name='patient_detail'),
    path('<int:pk>/edit/', patient_update, name='patient_update'),
    # Patient self-service portal pages
    path('my/appointments/<int:pk>/cancel/', patient_cancel_appointment, name='patient_cancel_appointment'),
    path('my/prescriptions/', patient_my_prescriptions, name='patient_my_prescriptions'),
    path('my/visits/', patient_my_visits, name='patient_my_visits'),
    path('my/lab-reports/', patient_my_lab_reports, name='patient_lab_reports'),
    
    # Doctor: Lab Reports
    path('doctor/lab-reports/', doctor_lab_reports, name='doctor_lab_reports'),

    # Lab reports staff actions
    path('lab-reports/<int:pk>/verify/', lab_report_verify, name='lab_report_verify'),
    path('lab-reports/<int:pk>/archive/', lab_report_archive, name='lab_report_archive'),

    # AI Assistant (patient-only)
    path('my/ai-ask/', patient_ai_ask, name='patient_ai_ask'),
]