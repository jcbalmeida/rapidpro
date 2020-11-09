from django.urls import reverse

from temba.tests import TembaTest
from temba.utils.text import random_string

from ...models import Channel
from .views import ClaimView


class KaleyraViewTest(TembaTest):
    def setUp(self):
        super().setUp()
        self.url = reverse("channels.types.kaleyra.claim")
        Channel.objects.all().delete()

    @property
    def valid_form(self):
        return {
            "country": "BR",
            "number": "31133087366",
            "account_sid": random_string(10),
            "api_key": random_string(10),
        }

    def submit_form(self, data):
        return self.client.post(self.url, data)

    def test_claim_page_is_available(self):
        self.login(self.admin)

        response = self.client.get(reverse("channels.channel_claim"), follow=True)
        self.assertContains(response, self.url)

        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    def test_claim(self):
        self.login(self.admin)

        post_data = self.valid_form
        response = self.submit_form(post_data)
        channel = Channel.objects.order_by("id").last()

        self.assertEqual(302, response.status_code)
        self.assertRedirect(response, reverse("channels.channel_configuration", args=[channel.uuid]))

    def test_required_fields(self):
        self.login(self.admin)

        response = self.submit_form({})
        self.assertEqual(200, response.status_code)
        self.assertFormError(response, "form", "number", "This field is required.")
        self.assertFormError(response, "form", "country", "This field is required.")
        self.assertFormError(response, "form", "account_sid", "This field is required.")
        self.assertFormError(response, "form", "api_key", "This field is required.")

    def test_invalid_phone_number(self):
        self.login(self.admin)

        post_data = self.valid_form
        post_data["number"] = "1234"  # invalid
        response = self.submit_form(post_data)
        self.assertEqual(200, response.status_code)
        self.assertFormError(response, "form", "number", ["Please enter a valid phone number"])
