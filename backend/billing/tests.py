import tempfile
import os
from unittest.mock import patch
from django.test import TestCase, Client
from django.urls import reverse
from accounts.models import CustomUser
from patients.models import Patient
from billing.models import Invoice

class InvoicePDFDownloadTest(TestCase):
    def setUp(self):
        self.patient_user = CustomUser.objects.create_user(
            username='patient1', password='pw', role='PATIENT'
        )
        self.patient_user.email = 'patient1@example.com' # Some code auth needs
        self.patient_user.save()
        
        self.patient = Patient.objects.create(
            user=self.patient_user,
            first_name='John',
            last_name='Doe',
            email='patient1@example.com',
            date_of_birth='1990-01-01'
        )
        
        self.staff_user = CustomUser.objects.create_user(
            username='accountant', password='pw', role='ACCOUNTANT'
        )
        
        self.other_patient = CustomUser.objects.create_user(
            username='patient2', password='pw', role='PATIENT'
        )
        self.other_patient.email = 'patient2@example.com'
        self.other_patient.save()
        
        self.other_patient_profile = Patient.objects.create(
            user=self.other_patient,
            first_name='Jane',
            last_name='Smith',
            email='patient2@example.com',
            date_of_birth='1990-01-01'
        )
        
        self.invoice = Invoice.objects.create(
            patient=self.patient,
            status='PAID',
            subtotal=100.0,
            grand_total=100.0,
        )
        self.client = Client()

    def test_pdf_download_success(self):
        self.client.login(username='patient1', password='pw')
        response = self.client.get(reverse('invoice_pdf_download', args=[self.invoice.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/pdf')
        self.assertTrue('attachment' in response['Content-Disposition'])

    def test_pdf_download_unauthorized(self):
        # Other patient accessing invoice
        self.client.login(username='patient2', password='pw')
        response = self.client.get(reverse('invoice_pdf_download', args=[self.invoice.pk]))
        self.assertEqual(response.status_code, 404)
        
    def test_pdf_download_staff(self):
        self.client.login(username='accountant', password='pw')
        response = self.client.get(reverse('invoice_pdf_download', args=[self.invoice.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/pdf')

    @patch('billing.utils.generate_invoice_pdf')
    def test_pdf_download_failure(self, mock_generate):
        mock_generate.side_effect = Exception("Mocked PDF failure")
        self.client.login(username='accountant', password='pw')
        response = self.client.get(reverse('invoice_pdf_download', args=[self.invoice.pk]), follow=True)
        # Should redirect to invoice_detail on failure
        self.assertRedirects(response, reverse('invoice_detail', args=[self.invoice.pk]))
        messages = list(response.context['messages'])
        self.assertTrue(any('PDF generation failed' in str(m) for m in messages))

class InvoiceManualEmailTest(TestCase):
    def setUp(self):
        self.patient_user = CustomUser.objects.create_user(
            username='patient1', password='pw', role='PATIENT'
        )
        self.patient = Patient.objects.create(
            user=self.patient_user,
            first_name='John',
            last_name='Doe',
            email='patient1@example.com',
            date_of_birth='1990-01-01'
        )
        self.accountant = CustomUser.objects.create_user(
            username='accountant', password='pw', role='ACCOUNTANT'
        )
        self.receptionist = CustomUser.objects.create_user(
            username='receptionist', password='pw', role='RECEPTIONIST'
        )
        self.invoice = Invoice.objects.create(
            patient=self.patient,
            status='PAID',
            subtotal=100.0,
            grand_total=100.0,
        )
        self.url = reverse('invoice_send_email_manual', args=[self.invoice.pk])
        self.client = Client()

    @patch('django.core.mail.send_mail')
    def test_manual_email_success_accountant(self, mock_send_mail):
        self.client.login(username='accountant', password='pw')
        response = self.client.post(self.url)
        self.assertRedirects(response, reverse('invoice_detail', args=[self.invoice.pk]))
        mock_send_mail.assert_called_once()
        self.assertEqual(mock_send_mail.call_args[1]['recipient_list'], ['patient1@example.com'])

    @patch('django.core.mail.send_mail')
    def test_manual_email_forbidden_for_receptionist(self, mock_send_mail):
        self.client.login(username='receptionist', password='pw')
        response = self.client.post(self.url)
        self.assertRedirects(response, reverse('dashboard'))
        mock_send_mail.assert_not_called()

    @patch('django.core.mail.send_mail')
    def test_manual_email_forbidden_for_patient(self, mock_send_mail):
        self.client.login(username='patient1', password='pw')
        response = self.client.post(self.url)
        self.assertRedirects(response, reverse('dashboard'))
        mock_send_mail.assert_not_called()
