from django.test import TestCase
from django.contrib.auth.models import User

from accounts.models import UserProfile
from animals.models import RescuedAnimal
from organizations.models import RescueOrganization
from reports.models import AnimalReport


class AnimalReportAssignmentTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='reporter', password='pw12345')

    def test_assigns_nearest_active_org_when_coordinates_are_present(self):
        far_org = RescueOrganization.objects.create(
            name='Far Test Org',
            contact_email='far@example.com',
            contact_phone='000',
            address='x',
            is_active=True,
            latitude=10.3157,
            longitude=123.8854,
        )
        near_org = RescueOrganization.objects.create(
            name='Near Test Org',
            contact_email='near@example.com',
            contact_phone='000',
            address='x',
            is_active=True,
            latitude=14.5995,
            longitude=120.9842,
        )

        self.client.force_login(self.user)
        response = self.client.post(
            '/api/report/submit/',
            {
                'animal_type': 'dog',
                'condition': 'injured',
                'priority': 'critical',
                'description': 'Test report near Manila',
                'location': 'Near Manila test location',
                'latitude': 14.6,
                'longitude': 120.98,
            },
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )

        self.assertEqual(response.status_code, 200)
        report = AnimalReport.objects.filter(reporter=self.user).latest('reported_at')
        self.assertEqual(report.rescue_org, near_org)
        self.assertNotEqual(report.rescue_org, far_org)

    def test_leaves_report_unassigned_when_coordinates_are_missing(self):
        self.client.force_login(self.user)
        response = self.client.post(
            '/api/report/submit/',
            {
                'animal_type': 'cat',
                'condition': 'stray',
                'priority': 'normal',
                'description': 'Test report with no coordinates',
                'location': 'Unknown location',
            },
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )

        self.assertEqual(response.status_code, 200)
        report = AnimalReport.objects.filter(reporter=self.user).latest('reported_at')
        self.assertIsNone(report.rescue_org)

    def test_updates_report_notes_and_creates_rescued_animal_when_rescued(self):
        org = RescueOrganization.objects.create(
            name='Phase-rescue-fix Org',
            contact_email='x@x.com',
            contact_phone='0',
            address='x',
            is_active=True,
        )
        org_user = User.objects.create_user(username='rescue_fix_org_user', password='testpass123')
        UserProfile.objects.update_or_create(user=org_user, defaults={'role': 'rescue_org', 'organization': org})

        reporter = User.objects.create_user(username='rescue_fix_reporter', password='testpass123')
        report = AnimalReport.objects.create(
            reporter=reporter,
            rescue_org=org,
            animal_type='dog',
            condition='injured',
            priority='critical',
            description='test',
            location='test location',
            status='pending',
        )

        self.client.force_login(org_user)
        response = self.client.post(
            f'/api/report/{report.id}/update/',
            {
                'status': 'rescued',
                'response_notes': 'We rescued this dog successfully.',
            },
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )

        self.assertEqual(response.status_code, 200)

        report.refresh_from_db()
        self.assertEqual(report.status, 'rescued')
        self.assertEqual(report.response_notes, 'We rescued this dog successfully.')

        animal = RescuedAnimal.objects.filter(source_report=report).first()
        self.assertIsNotNone(animal)
        self.assertEqual(animal.status, 'recovering')
        self.assertEqual(animal.rescue_org, org)
