import os
import shutil
import tempfile

from django.test import TestCase, Client, override_settings
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.auth.models import User

from core.models import AnimalReport, AnimalReportPhoto, RescueOrganization, UserProfile


class ReportSubmissionTests(TestCase):
    def setUp(self):
        self.media_root = tempfile.mkdtemp()
        self.override = override_settings(MEDIA_ROOT=self.media_root)
        self.override.enable()

        self.reporter = User.objects.create_user(username='reporter', password='reporterpw')
        UserProfile.objects.create(user=self.reporter, role='reporter')

        self.organization = RescueOrganization.objects.create(
            name='Rescue One',
            contact_email='org@example.com',
            contact_phone='555-0100',
            address='123 Rescue Ln',
            is_active=True,
        )

        self.client = Client()

    def tearDown(self):
        self.override.disable()
        shutil.rmtree(self.media_root, ignore_errors=True)

    def test_report_submit_requires_authentication(self):
        response = self.client.post(reverse('user_submit_report'), {
            'animal_type': 'dog',
            'condition': 'stray',
            'priority': 'normal',
            'description': 'Found a stray dog',
            'location': '123 Main St',
        })
        self.assertEqual(response.status_code, 401)
        data = response.json()
        self.assertFalse(data.get('ok'))
        self.assertEqual(data.get('error'), 'Authentication required.')

    def test_report_submit_saves_report_and_photos(self):
        self.client.login(username='reporter', password='reporterpw')

        photo_file = SimpleUploadedFile(
            name='report.jpg',
            content=b'\x47\x49\x46\x38\x39\x61',
            content_type='image/jpeg',
        )
        second_photo = SimpleUploadedFile(
            name='report2.jpg',
            content=b'\x47\x49\x46\x38\x39\x61',
            content_type='image/jpeg',
        )

        response = self.client.post(
            reverse('user_submit_report'),
            {
                'animal_type': 'dog',
                'condition': 'stray',
                'priority': 'high',
                'description': 'Found a stray puppy near the park.',
                'location': '789 Park Ave',
                'latitude': '40.7128',
                'longitude': '-74.0060',
                'photo': photo_file,
                'photos': [second_photo],
            },
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data.get('ok'))
        self.assertIn('report_id', data)
        self.assertEqual(data.get('report_number'), data.get('report_id'))

        report = AnimalReport.objects.get(pk=data['report_id'])
        self.assertEqual(report.reporter, self.reporter)
        self.assertEqual(report.location, '789 Park Ave')
        self.assertEqual(report.latitude, 40.7128)
        self.assertEqual(report.longitude, -74.0060)
        self.assertTrue(report.photo.name.startswith('animal_photos/'))
        self.assertEqual(report.photos.count(), 1)

    def test_report_submit_rejects_invalid_photo_type(self):
        self.client.login(username='reporter', password='reporterpw')

        invalid_file = SimpleUploadedFile(
            name='report.txt',
            content=b'not-an-image',
            content_type='text/plain',
        )

        response = self.client.post(
            reverse('user_submit_report'),
            {
                'animal_type': 'cat',
                'condition': 'sick',
                'priority': 'normal',
                'description': 'Cat appears ill.',
                'location': '456 Elm St',
                'photo': invalid_file,
            },
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )

        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertFalse(data.get('ok'))
        self.assertEqual(data.get('error'), 'Only image files are allowed for report photos.')
