from django.test import TestCase, Client
from django.urls import reverse

class ForgotPasswordTemplateTest(TestCase):
    def test_request_page_renders(self):
        client = Client()
        response = client.get(reverse('patient_forgot_password_request'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'accounts/forgot_password_request.html')
        self.assertTemplateUsed(response, 'base.html')
