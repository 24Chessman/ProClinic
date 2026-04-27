from django.test import TestCase, Client
from django.urls import reverse
from .models import CustomUser

class ForgotPasswordTemplateTest(TestCase):
    def test_request_page_renders(self):
        client = Client()
        response = client.get(reverse('patient_forgot_password_request'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'accounts/forgot_password_request.html')
        self.assertTemplateUsed(response, 'base.html')

class StaffProfileViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.staff_user = CustomUser.objects.create_user(
            username='doctor1',
            email='doctor@test.com',
            password='password123',
            role='DOCTOR',
            first_name='John',
            last_name='Doe'
        )
        self.url = reverse('staff_profile')
        
    def test_get_staff_profile_returns_200(self):
        self.client.login(username='doctor1', password='password123')
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'accounts/staff_profile.html')
        self.assertIn('form', response.context)
        
    def test_invalid_post_re_renders_form(self):
        self.client.login(username='doctor1', password='password123')
        # Assuming last_name is required in the form, submitting an empty string should fail
        response = self.client.post(self.url, {'first_name': 'Jane', 'last_name': ''})
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'accounts/staff_profile.html')
        self.assertIn('form', response.context)
        self.assertTrue(response.context['form'].errors)
        
    def test_valid_post_saves_successfully(self):
        self.client.login(username='doctor1', password='password123')
        response = self.client.post(self.url, {'first_name': 'Jane', 'last_name': 'Smith', 'email': 'jane.smith@test.com'})
        # Should redirect on success
        self.assertRedirects(response, self.url)
        # Check if user was updated
        self.staff_user.refresh_from_db()
        self.assertEqual(self.staff_user.first_name, 'Jane')
        self.assertEqual(self.staff_user.last_name, 'Smith')
