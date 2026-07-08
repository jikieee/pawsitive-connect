from unittest.mock import patch

from django.test import RequestFactory, SimpleTestCase

from core.views import _validate_recaptcha


class RecaptchaValidationTests(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def test_missing_captcha_token_is_rejected(self):
        request = self.factory.post('/login/')
        self.assertFalse(_validate_recaptcha(request))

    @patch('core.views.urllib.request.urlopen')
    def test_successful_captcha_verification_is_accepted(self, mock_urlopen):
        mock_urlopen.return_value.__enter__.return_value.read.return_value = b'{"success": true}'
        request = self.factory.post('/login/', {'g-recaptcha-response': 'token-123'})

        self.assertTrue(_validate_recaptcha(request))
