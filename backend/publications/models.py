from django.db import models
from django.conf import settings
from django.utils import timezone
from django.core.files.storage import storages

def select_raw_storage():
    return storages['raw']

class Publication(models.Model):
    STATUS_DRAFT    = 'DRAFT'
    STATUS_PENDING  = 'PENDING'
    STATUS_APPROVED = 'APPROVED'
    STATUS_REJECTED = 'REJECTED'

    STATUS_CHOICES = [
        (STATUS_DRAFT,    'Draft'),
        (STATUS_PENDING,  'Pending Approval'),
        (STATUS_APPROVED, 'Approved'),
        (STATUS_REJECTED, 'Rejected'),
    ]

    # ── Core fields ───────────────────────────────────────────────────────────
    doctor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='publications',
    )
    title    = models.CharField(max_length=255)
    abstract = models.TextField()
    authors  = models.CharField(
        max_length=500,
        help_text='Comma-separated list of authors.',
    )
    pdf_file = models.FileField(upload_to='publications/papers/', storage=select_raw_storage)
    status   = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_DRAFT,
        db_index=True,
    )

    # ── Admin / review fields ─────────────────────────────────────────────────
    admin_notes      = models.TextField(blank=True, help_text='Internal notes from the reviewer.')
    rejection_reason = models.TextField(blank=True, help_text='Reason shown to the doctor on rejection.')
    approved_by      = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='approved_publications',
        help_text='Admin/staff who approved this paper.',
    )
    approved_at = models.DateTimeField(null=True, blank=True, help_text='Timestamp of approval.')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} — {self.doctor.get_full_name() or self.doctor.username} ({self.status})"

    # ── Convenience methods ───────────────────────────────────────────────────

    def approve(self, reviewer):
        """Approve the paper and record who approved it and when."""
        self.status           = self.STATUS_APPROVED
        self.approved_by      = reviewer
        self.approved_at      = timezone.now()
        self.rejection_reason = ''
        self.save(update_fields=['status', 'approved_by', 'approved_at', 'rejection_reason', 'updated_at'])

    def reject(self, reviewer, reason=''):
        """Reject the paper with an optional reason shown to the submitting doctor."""
        self.status           = self.STATUS_REJECTED
        self.rejection_reason = reason
        self.approved_by      = None
        self.approved_at      = None
        self.save(update_fields=['status', 'rejection_reason', 'approved_by', 'approved_at', 'updated_at'])

    @property
    def is_public(self):
        return self.status == self.STATUS_APPROVED