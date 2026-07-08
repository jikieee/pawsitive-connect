from django.test import TestCase
from django.contrib.auth import get_user_model

from core.models import (
    RescueOrganization,
    UserProfile,
    AnimalReport,
    RescuedAnimal,
    Announcement,
    AdoptionInquiry,
    Message,
)


class OrganizationDashboardViewTests(TestCase):
    def setUp(self):
        self.user_model = get_user_model()
        self.user = self.user_model.objects.create_user(username='orgdash', password='pw12345')
        self.org = RescueOrganization.objects.create(
            name='Paws Org',
            contact_email='org@example.com',
            contact_phone='123456789',
            address='Test Street',
        )
        UserProfile.objects.create(user=self.user, role='rescue_org', organization=self.org)

    def test_org_dashboard_overview_renders_with_live_counts(self):
        AnimalReport.objects.create(
            reporter=self.user,
            rescue_org=self.org,
            animal_type='dog',
            condition='injured',
            status='pending',
            priority='critical',
            description='Needs help',
            location='Main Street',
        )
        RescuedAnimal.objects.create(
            rescue_org=self.org,
            species='dog',
            name='Buddy',
            status='recovering',
            shelter='Shelter A',
        )

        self.client.force_login(self.user)
        response = self.client.get('/dashboard/')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Active Rescue Cases')
        self.assertContains(response, 'Under Recovery')
        self.assertContains(response, 'Ready for Adoption')
        self.assertContains(response, 'New Reports Today')

    def test_org_dashboard_renders_announcements_inquiries_and_messages(self):
        animal = RescuedAnimal.objects.create(
            rescue_org=self.org,
            species='cat',
            name='Mochi',
            status='adoption',
            shelter='Shelter B',
        )
        Announcement.objects.create(
            rescue_org=self.org,
            posted_by=self.user,
            type='adoption',
            title='Adoption day',
            body='Mochi is ready to meet new families.',
        )
        other_user = self.user_model.objects.create_user(username='alice', password='pw12345')
        AdoptionInquiry.objects.create(
            user=other_user,
            animal=animal,
            rescue_org=self.org,
            message='I would love to adopt Mochi.',
        )
        Message.objects.create(
            sender=other_user,
            recipient=self.user,
            subject='Adoption question',
            body='Can I visit Mochi this weekend?',
        )

        self.client.force_login(self.user)
        response = self.client.get('/dashboard/')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Adoption day')
        self.assertContains(response, 'Mochi is ready to meet new families.')
        self.assertContains(response, 'alice')
        self.assertContains(response, 'Adoption question')
