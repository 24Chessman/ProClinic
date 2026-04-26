from django.db import models
from django.core.exceptions import ValidationError
from patients.models import Patient
from appointments.models import Appointment

class MedicineMaster(models.Model):
    name = models.CharField(max_length=255, unique=True, help_text="Common name of the medicine")
    default_price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    description = models.TextField(blank=True, null=True, help_text="Optional descriptions or default instructions")

    def __str__(self):
        return f"{self.name} - ${self.default_price}"

class Invoice(models.Model):
    STATUS_CHOICES = [
        ('DRAFT',    'Draft'),
        ('UNPAID',   'Unpaid'),
        ('PARTIAL',  'Partially Paid'),
        ('PAID',     'Paid'),
        ('REFUNDED', 'Refunded / Cancelled'),
    ]

    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='invoices')
    appointment = models.OneToOneField(Appointment, on_delete=models.SET_NULL, null=True, blank=True, related_name='invoice')
    
    # Financial Breakdown
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    grand_total = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    
    paid_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    due_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

    # Note: total_amount is kept for backward-compatibility but matches grand_total
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='UNPAID')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    pdf_file   = models.FileField(upload_to='invoices/pdfs/', null=True, blank=True)

    def clean(self):
        if any(v < 0 for v in [self.subtotal, self.tax_amount, self.discount_amount, self.grand_total, self.paid_amount, self.due_amount]):
            raise ValidationError("Financial amounts cannot be negative.")

    def recalculate_totals(self):
        """Recompute subtotal and grand_total from current line items.

        Call after adding/removing InvoiceItems and save() the instance
        to persist updated values.
        """
        from decimal import Decimal
        subtotal = sum(item.line_total for item in self.items.all())
        self.subtotal     = subtotal
        self.grand_total  = subtotal - self.discount_amount + self.tax_amount
        self.total_amount = self.grand_total
        self.due_amount   = self.grand_total - self.paid_amount

    def __str__(self):
        return f"Invoice {self.id} - {self.patient} ({self.status})"

class InvoiceItem(models.Model):
    ITEM_TYPES = [
        ('CONSULTATION', 'Consultation'),
        ('MEDICINE', 'Medicine'),
        ('LAB', 'Lab / Test'),
        ('PROCEDURE', 'Procedure / Service'),
        ('OTHER', 'Other'),
    ]

    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='items')
    item_type = models.CharField(max_length=50, choices=ITEM_TYPES, default='OTHER')
    service_name = models.CharField(max_length=255, help_text="e.g., General Consultation, Paracetamol")
    notes = models.CharField(max_length=255, blank=True, null=True, help_text="Optional dosage or details")
    unit_cost = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField(default=1)

    @property
    def line_total(self):
        return self.unit_cost * self.quantity

    def clean(self):
        if self.unit_cost < 0:
            raise ValidationError("Unit cost cannot be negative.")

    def __str__(self):
        return f"[{self.get_item_type_display()}] {self.service_name} for Invoice {self.invoice.id}"