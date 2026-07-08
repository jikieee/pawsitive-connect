from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse

from core.models import UserProfile, RescueOrganization, AnimalReport, RescuedAnimal


class AdminDashboardViewTests(TestCase):
    def setUp(self):
        self.user_model = get_user_model()
        self.admin = self.user_model.objects.create_user(
            username='adminuser',
            password='pw12345',
            is_staff=True,
        )
        UserProfile.objects.create(user=self.admin, role='admin')
        self.reporter = self.user_model.objects.create_user(username='reporter', password='pw12345')
        UserProfile.objects.create(user=self.reporter, role='reporter')
        self.org = RescueOrganization.objects.create(
            name='Admin Test Rescue',
            contact_email='rescue@example.com',
            contact_phone='09171234567',
            address='Admin Test Street',
        )
        self.report = AnimalReport.objects.create(
            reporter=self.reporter,
            rescue_org=self.org,
            animal_type='dog',
            condition='injured',
            priority='critical',
            status='pending',
            description='Needs admin review',
            location='Admin Test Location',
        )
        RescuedAnimal.objects.create(
            rescue_org=self.org,
            species='dog',
            name='Admin Buddy',
            status='adoption',
            shelter='Admin Shelter',
            adoption_open=True,
        )

    def test_admin_dashboard_renders_database_driven_sections(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Admin Dashboard')
        self.assertContains(response, 'User Management')
        self.assertContains(response, 'Rescue Organization Management')
        self.assertContains(response, 'Report Management')
        self.assertContains(response, 'Animal Management')
        self.assertContains(response, 'Admin Test Rescue')
        self.assertContains(response, 'Admin Test Location')
        self.assertContains(response, 'Admin Buddy')

    def test_admin_can_toggle_organization_active_status(self):
        self.client.force_login(self.admin)
        response = self.client.post(reverse('admin_toggle_org_active', args=[self.org.pk]))
        self.assertEqual(response.status_code, 302)
        self.org.refresh_from_db()
        self.assertFalse(self.org.is_active)

    def test_admin_can_update_report_status(self):
        self.client.force_login(self.admin)
        response = self.client.post(reverse('admin_update_report_status', args=[self.report.pk]), {'status': 'responding'})
        self.assertEqual(response.status_code, 302)
        self.report.refresh_from_db()
        self.assertEqual(self.report.status, 'responding')
