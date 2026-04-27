from django.urls import path
from .views import (
    generate_invoice,
    invoice_edit_draft,
    patient_invoices,
    invoice_list,
    invoice_detail,
    invoice_update_status,
    api_medicines,
    api_prescription_context,
    api_patient_appointments,
    invoice_pdf_download,
    medicine_list,
    medicine_create,
    medicine_delete,
    invoice_send_email_manual,
)

urlpatterns = [
    # Staff: generate new invoice
    path('new/', generate_invoice, name='generate_invoice'),

    # Patient: read-only self-service
    path('my-invoices/', patient_invoices, name='patient_invoices'),

    # Accountant / Admin: management
    path('manage/', invoice_list, name='invoice_list'),
    path('manage/<int:pk>/', invoice_detail, name='invoice_detail'),
    path('manage/<int:pk>/edit/', invoice_edit_draft, name='invoice_edit_draft'),
    path('manage/<int:pk>/status/', invoice_update_status, name='invoice_update_status'),
    path('manage/<int:pk>/pdf/', invoice_pdf_download, name='invoice_pdf_download'),
    path('manage/<int:pk>/send-email/', invoice_send_email_manual, name='invoice_send_email_manual'),

    # Medicine catalog CRUD
    path('medicines/', medicine_list, name='medicine_list'),
    path('medicines/add/', medicine_create, name='medicine_create'),
    path('medicines/<int:pk>/delete/', medicine_delete, name='medicine_delete'),

    # APIs for dynamic frontend billing
    path('api/medicines/', api_medicines, name='api_medicines'),
    path('api/prescription_context/', api_prescription_context, name='api_prescription_context'),
    path('api/patient_appointments/', api_patient_appointments, name='api_patient_appointments'),
]