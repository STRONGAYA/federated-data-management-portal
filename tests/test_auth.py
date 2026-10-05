import unittest

from federated_data_management_portal.auth import authenticated_email_from_headers


class AuthenticatedEmailFromHeadersTests(unittest.TestCase):
    def test_returns_forwarded_email(self):
        headers = {"X-Auth-Request-Email": "person@example.org"}

        self.assertEqual(authenticated_email_from_headers(headers), "person@example.org")

    def test_strips_surrounding_whitespace(self):
        headers = {"X-Auth-Request-Email": "  person@example.org  "}

        self.assertEqual(authenticated_email_from_headers(headers), "person@example.org")

    def test_returns_empty_string_when_header_is_missing(self):
        self.assertEqual(authenticated_email_from_headers({}), "")


if __name__ == "__main__":
    unittest.main()
