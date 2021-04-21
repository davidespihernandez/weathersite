from django.contrib.auth import get_user_model
from django.test import override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase


class TestLimitedEndpoint(APITestCase):
    @override_settings(DEFAULT_RATE_LIMIT_PER_MINUTE=2)
    def test_limited_anonymous_returns_headers_and_limits(self):
        """
        Given an endpoint with a limited rate of 2 requests per minute for anonymous users
        When we perform 3 requests in less than a minute
        The first and second ones return the headers X-CURRENT-RATE-LIMIT and X-REMAINING-CALLS
        The third one will be rejected with a HTTP 429
        """
        url = reverse('limited')
        with self.subTest("The first call returns current rate 2 and remaining 1"):
            response = self.client.get(url)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(int(response["X-CURRENT-RATE-LIMIT"]), 2)
            self.assertEqual(int(response["X-REMAINING-CALLS"]), 1)

        with self.subTest("The second call returns current rate 2 and remaining 0"):
            response = self.client.get(url)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(int(response["X-CURRENT-RATE-LIMIT"]), 2)
            self.assertEqual(int(response["X-REMAINING-CALLS"]), 0)

        with self.subTest("The third call returns HTTP 429"):
            response = self.client.get(url)
            self.assertEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)

    @override_settings(DEFAULT_RATE_LIMIT_PER_MINUTE=2)
    def test_limited_authenticated_user_is_not_limited(self):
        """
        Given an endpoint with a limited rate of 2 requests per minute for anonymous users
        When we perform 3 requests in less than a minute for an authenticated user
        Then no headers are returned, and the requests are allowed
        """
        url = reverse('limited')
        # create a user to authenticate the requests
        user_model = get_user_model()
        user = user_model(username="user")
        user.set_password("password")
        user.save()
        # authenticate
        self.client.force_login(user)

        with self.subTest("The first call doesn't return headers"):
            response = self.client.get(url)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertTrue("X-CURRENT-RATE-LIMIT" not in response)
            self.assertTrue("X-REMAINING-CALLS" not in response)

        with self.subTest("The second call doesn't return headers"):
            response = self.client.get(url)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertTrue("X-CURRENT-RATE-LIMIT" not in response)
            self.assertTrue("X-REMAINING-CALLS" not in response)

        with self.subTest("The third call doesn't return headers"):
            response = self.client.get(url)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertTrue("X-CURRENT-RATE-LIMIT" not in response)
            self.assertTrue("X-REMAINING-CALLS" not in response)
