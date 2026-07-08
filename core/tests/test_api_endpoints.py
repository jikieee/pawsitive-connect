from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse

from core.models import RescueOrganization, RescuedAnimal, UserProfile, AdoptionInquiry


class ApiEndpointTests(TestCase):
    def setUp(self):
        self.user_model = get_user_model()
        self.user = self.user_model.objects.create_user(username='tester', password='pw12345')
        self.org = RescueOrganization.objects.create(
            name='Test Rescue',
            contact_email='org@example.com',
            contact_phone='1234567890',
            address='123 Test St',
        )
        UserProfile.objects.create(user=self.user, role='rescue_org', organization=self.org)

        self.animal = RescuedAnimal.objects.create(
            rescue_org=self.org,
            name='Buddy',
            species='dog',
            sex='male',
            status='adoption',
            vaccination='complete',
            shelter='Test Shelter',
            adoption_open=True,
        )

        self.inquiry = AdoptionInquiry.objects.create(
            user=self.user,
            animal=self.animal,
            rescue_org=self.org,
            message='Interested in adopting',
        )

    def test_rescue_organizations_api(self):
        url = reverse('rescue_organizations_api')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers.get('Content-Type').split(';')[0], 'application/json')
        self.assertEqual(response.json()[0]['name'], 'Test Rescue')

    def test_rescued_animals_api(self):
        url = reverse('rescued_animals_api')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()[0]['name'], 'Buddy')

    def test_adoption_inquiries_api(self):
        self.client.force_login(self.user)
        url = reverse('adoption_inquiries_api')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()[0]['message'], 'Interested in adopting')
