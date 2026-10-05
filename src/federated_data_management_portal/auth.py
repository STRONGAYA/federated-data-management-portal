"""Helpers for identity information supplied by the authentication proxy."""

AUTHENTICATED_EMAIL_HEADER = "X-Auth-Request-Email"


def authenticated_email_from_headers(headers):
    """Return the authenticated email supplied by oauth2-proxy, if present."""
    email = headers.get(AUTHENTICATED_EMAIL_HEADER, "")
    return email.strip() if isinstance(email, str) else ""
