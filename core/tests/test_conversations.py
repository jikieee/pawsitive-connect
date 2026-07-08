from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from core.models import Conversation, Message, Notification, UserProfile, AdoptionInquiry
from animals.models import RescuedAnimal
from organizations.models import RescueOrganization


class ConversationTests(TestCase):
    def setUp(self):
        # Reporter (default role)
        self.reporter = User.objects.create_user(username='rpt', password='rptpw', email='rpt@example.com')

        # Org user (will set profile role)
        self.org = User.objects.create_user(username='org', password='orgpw', email='org@example.com')
        UserProfile.objects.create(user=self.org, role='rescue_org')

        self.client = Client()

    def test_user_send_message_creates_conversation(self):
        self.client.login(username='rpt', password='rptpw')
        resp = self.client.post(reverse('user_send_message'), {
            'recipient_id': self.org.pk,
            'body': 'Hello from reporter',
            'subject': 'Hi'
        })
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data.get('ok'))
        msg_id = data.get('message_id')

        msg = Message.objects.get(pk=msg_id)
        self.assertIsNotNone(msg.conversation)
        conv = msg.conversation
        self.assertIn(self.reporter, conv.participants.all())
        self.assertIn(self.org, conv.participants.all())
        self.assertEqual(conv.last_message, msg)

    def test_org_send_message_creates_conversation(self):
        self.client.login(username='org', password='orgpw')
        resp = self.client.post(reverse('org_send_message'), {
            'recipient_id': self.reporter.pk,
            'body': 'Reply from org',
            'subject': 'Re'
        })
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data.get('ok'))
        msg = Message.objects.get(pk=data.get('message_id'))
        self.assertIsNotNone(msg.conversation)
        conv = msg.conversation
        self.assertIn(self.reporter, conv.participants.all())
        self.assertIn(self.org, conv.participants.all())
        self.assertEqual(conv.last_message, msg)

    def test_send_with_existing_conversation_appends(self):
        # create conversation first
        conv = Conversation.objects.create(subject='Existing')
        conv.participants.add(self.reporter, self.org)

        self.client.login(username='rpt', password='rptpw')
        resp = self.client.post(reverse('user_send_message'), {
            'recipient_id': self.org.pk,
            'body': 'Another message',
            'conversation_id': conv.pk,
        })
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        msg = Message.objects.get(pk=data.get('message_id'))
        self.assertEqual(msg.conversation, conv)
        conv.refresh_from_db()
        self.assertEqual(conv.last_message, msg)

    def test_user_send_message_notifies_org(self):
        self.client.login(username='rpt', password='rptpw')
        resp = self.client.post(reverse('user_send_message'), {
            'recipient_id': self.org.pk,
            'body': 'Hello rescue team',
        })
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(Notification.objects.filter(recipient=self.org, type='new_user_message', body__icontains='Hello rescue team').exists())

    def test_inquiry_submission_creates_shared_thread(self):
        org = RescueOrganization.objects.create(name='Paws Rescue', contact_email='paws@example.com', contact_phone='123', address='123 Main')
        UserProfile.objects.update_or_create(user=self.org, defaults={'role': 'rescue_org', 'organization': org})
        animal = RescuedAnimal.objects.create(
            rescue_org=org,
            name='Mochi',
            species='dog',
            status='adoption',
            adoption_open=True,
        )

        self.client.login(username='rpt', password='rptpw')
        resp = self.client.post(reverse('user_send_inquiry'), {
            'animal_id': animal.pk,
            'message': 'I want to adopt Mochi',
            'living_situation': 'house',
            'other_pets': 'none',
        })

        self.assertEqual(resp.status_code, 200)
        inquiry = AdoptionInquiry.objects.get(user=self.reporter, animal=animal)
        msg = Message.objects.filter(inquiry=inquiry).first()
        self.assertIsNotNone(msg)
        self.assertIsNotNone(msg.conversation)
        self.assertTrue(msg.conversation.participants.filter(pk=self.reporter.pk).exists())
        self.assertTrue(msg.conversation.participants.filter(pk=self.org.pk).exists())
        self.assertTrue(Notification.objects.filter(recipient=self.org, type='new_inquiry').exists())

    def test_org_send_message_notifies_reporter(self):
        self.client.login(username='org', password='orgpw')
        resp = self.client.post(reverse('org_send_message'), {
            'recipient_id': self.reporter.pk,
            'body': 'Reply from org',
        })
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(Notification.objects.filter(recipient=self.reporter, type='org_reply', body__icontains='Reply from org').exists())

    def test_message_thread_api_marks_messages_read(self):
        conv = Conversation.objects.create(subject='Hello thread')
        conv.participants.add(self.reporter, self.org)
        Message.objects.create(
            sender=self.org,
            recipient=self.reporter,
            conversation=conv,
            body='Org reply',
            is_read=False,
        )
        Message.objects.create(
            sender=self.reporter,
            recipient=self.org,
            conversation=conv,
            body='Reporter question',
            is_read=True,
        )

        self.client.login(username='rpt', password='rptpw')
        resp = self.client.get(reverse('message_thread_api', args=[self.org.pk]))
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data.get('conversation_id'), conv.pk)
        self.assertEqual(len(data.get('messages', [])), 2)
        self.assertTrue(Message.objects.filter(sender=self.org, recipient=self.reporter, is_read=True).exists())

    def test_conversations_api_returns_unread_and_participants(self):
        conv = Conversation.objects.create(subject='User to org')
        conv.participants.add(self.reporter, self.org)
        Message.objects.create(
            sender=self.org,
            recipient=self.reporter,
            conversation=conv,
            body='Hello reporter',
            is_read=False,
        )

        self.client.login(username='rpt', password='rptpw')
        resp = self.client.get(reverse('conversations_api'))
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(len(data.get('conversations', [])), 1)
        conversation = data['conversations'][0]
        self.assertEqual(conversation['unread'], 1)
        self.assertEqual(conversation['participants'][0]['id'], self.org.pk)
