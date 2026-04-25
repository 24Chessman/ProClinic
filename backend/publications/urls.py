from django.urls import path
from . import views

urlpatterns = [
    # Public (unauthenticated)
    path('', views.public_list, name='publications_public_list'),
    path('<int:pk>/', views.public_detail, name='publications_public_detail'),

    # Patient portal (login required)
    path('patient/', views.patient_publications, name='patient_publications'),

    # Doctor
    path('submit/', views.submit_paper, name='submit_paper'),
    path('my-papers/', views.doctor_dashboard, name='doctor_my_papers'),

    # Admin
    path('review/', views.admin_approval_panel, name='admin_approval_panel'),
    path('<int:pk>/approve/', views.admin_approve, name='admin_approve_paper'),
    path('<int:pk>/reject/', views.admin_reject, name='admin_reject_paper'),
]