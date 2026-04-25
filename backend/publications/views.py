"""
publications/views.py
─────────────────────
Web (template-based) views for the research publication workflow.

Routes
------
Public (no auth required):
  /publications/                     → public_list
  /publications/<pk>/                → public_detail

Doctor:
  /publications/submit/              → submit_paper  (existing)
  /publications/my-papers/           → doctor_dashboard

Admin:
  /publications/review/              → admin_approval_panel
  /publications/<pk>/approve/        → admin_approve   (POST)
  /publications/<pk>/reject/         → admin_reject    (POST)
"""

from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import get_object_or_404, redirect, render

from .forms import PublicationForm
from .models import Publication


# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────

def _is_admin(user):
    return user.is_authenticated and (user.is_staff or user.is_superuser or getattr(user, 'role', '') == 'ADMIN')


# ──────────────────────────────────────────────────────────────────────────────
# Public views (no auth)
# ──────────────────────────────────────────────────────────────────────────────

def public_list(request):
    """Publicly visible listing of APPROVED research papers."""
    papers = (
        Publication.objects
        .filter(status=Publication.STATUS_APPROVED)
        .select_related('doctor')
        .order_by('-approved_at')
    )
    return render(request, 'publications/public_list.html', {'papers': papers})


def public_detail(request, pk):
    """Full detail page for a single APPROVED paper."""
    paper = get_object_or_404(Publication, pk=pk, status=Publication.STATUS_APPROVED)
    return render(request, 'publications/public_detail.html', {'paper': paper})


# ──────────────────────────────────────────────────────────────────────────────
# Patient portal view (login required, approved papers only)
# ──────────────────────────────────────────────────────────────────────────────

@login_required
def patient_publications(request):
    """Patient portal: browse approved research papers. PATIENT role only."""
    if request.user.role != 'PATIENT':
        return redirect('dashboard')

    papers = (
        Publication.objects
        .filter(status=Publication.STATUS_APPROVED)
        .select_related('doctor')
        .order_by('-approved_at')
    )
    return render(request, 'publications/patient_list.html', {'papers': papers})


# ──────────────────────────────────────────────────────────────────────────────
# Doctor views
# ──────────────────────────────────────────────────────────────────────────────

@login_required
def submit_paper(request):
    """Upload a new research paper (status → DRAFT or PENDING). DOCTOR only."""
    if request.user.role != 'DOCTOR':
        return redirect('dashboard')
    if request.method == 'POST':
        form = PublicationForm(request.POST, request.FILES)
        if form.is_valid():
            publication = form.save(commit=False)
            publication.doctor = request.user
            if request.POST.get('action') == 'draft':
                publication.status = Publication.STATUS_DRAFT
            else:
                publication.status = Publication.STATUS_PENDING
            publication.save()
            messages.success(request, "Publication saved as draft." if publication.status == 'DRAFT' else "Publication submitted for review.")
            return redirect('doctor_my_papers')
    else:
        form = PublicationForm()
    return render(request, 'publications/submit_paper.html', {'form': form})


@login_required
def doctor_dashboard(request):
    """Doctor's own paper list and drafts. DOCTOR only."""
    if request.user.role != 'DOCTOR':
        return redirect('dashboard')
    papers = (
        Publication.objects
        .filter(doctor=request.user)
        .exclude(status='DRAFT')
        .order_by('-created_at')
    )
    drafts = Publication.objects.filter(status='DRAFT', doctor=request.user).order_by('-created_at')
    return render(request, 'publications/doctor_dashboard.html', {'papers': papers, 'drafts': drafts})


# ──────────────────────────────────────────────────────────────────────────────
# Admin views
# ──────────────────────────────────────────────────────────────────────────────

@user_passes_test(_is_admin)
def admin_approval_panel(request):
    """Admin panel: pending papers + recent decisions."""
    pending  = Publication.objects.filter(status=Publication.STATUS_PENDING).select_related('doctor').order_by('created_at')
    approved = Publication.objects.filter(status=Publication.STATUS_APPROVED).select_related('doctor', 'approved_by').order_by('-approved_at')[:10]
    rejected = Publication.objects.filter(status=Publication.STATUS_REJECTED).select_related('doctor').order_by('-updated_at')[:10]
    return render(request, 'publications/admin_approval.html', {
        'pending':  pending,
        'approved': approved,
        'rejected': rejected,
    })


@user_passes_test(_is_admin)
def admin_approve(request, pk):
    """POST — approve a paper."""
    if request.method != 'POST':
        return redirect('admin_approval_panel')
    paper = get_object_or_404(Publication, pk=pk)
    paper.approve(reviewer=request.user)
    messages.success(request, f'"{paper.title}" has been approved and is now publicly visible.')
    return redirect('admin_approval_panel')


@user_passes_test(_is_admin)
def admin_reject(request, pk):
    """POST — reject a paper with an optional reason."""
    if request.method != 'POST':
        return redirect('admin_approval_panel')
    paper  = get_object_or_404(Publication, pk=pk)
    reason = request.POST.get('rejection_reason', '').strip()
    paper.reject(reviewer=request.user, reason=reason)
    messages.warning(request, f'"{paper.title}" has been rejected.')
    return redirect('admin_approval_panel')