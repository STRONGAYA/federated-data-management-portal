import json
import tempfile
import unittest
from pathlib import Path

from federated_data_management_portal.main import Dashboard


class AuthenticatedEmailCallbackTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp_dir = tempfile.TemporaryDirectory()
        data_dir = Path(cls.temp_dir.name)
        schema_path = data_dir / "schema.jsonld"
        dashboard_path = data_dir / "dashboard.json"
        schema_path.write_text(json.dumps({}), encoding="utf-8")
        dashboard_path.write_text(
            json.dumps({"2026-01-01T00:00:00": {}}),
            encoding="utf-8",
        )

        cls.dashboard = Dashboard(schema_path, dashboard_path)
        cls.client = cls.dashboard.App.server.test_client()

    @classmethod
    def tearDownClass(cls):
        cls.temp_dir.cleanup()

    def request_email_update(self, headers=None):
        return self.client.post(
            "/_dash-update-component",
            headers=headers,
            json={
                "output": "authenticated-user-email.children",
                "outputs": {
                    "id": "authenticated-user-email",
                    "property": "children",
                },
                "inputs": [{"id": "url", "property": "pathname", "value": "/"}],
                "changedPropIds": ["url.pathname"],
                "state": [],
            },
        )

    def test_displays_email_forwarded_by_authentication_proxy(self):
        response = self.request_email_update(
            headers={"X-Auth-Request-Email": "person@example.org"}
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.get_json()["response"]["authenticated-user-email"]["children"],
            "person@example.org",
        )

    def test_displays_nothing_without_proxy_header(self):
        response = self.request_email_update()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.get_json()["response"]["authenticated-user-email"]["children"],
            "",
        )

    def test_account_actions_have_expected_destinations(self):
        import dash

        def find_by_id(component, wanted):
            if getattr(component, "id", None) == wanted:
                return component
            children = getattr(component, "children", None)
            if children is None:
                return None
            if not isinstance(children, (list, tuple)):
                children = [children]
            for child in children:
                found = find_by_id(child, wanted)
                if found is not None:
                    return found
            return None

        # the identity container lives in the notice banner of every page layout
        account_container = None
        for page in dash.page_registry.values():
            account_container = find_by_id(page["layout"], "authenticated-user-container")
            if account_container is not None:
                break
        self.assertIsNotNone(account_container)
        sign_out, manage_permissions = account_container.children[1].children

        self.assertEqual(sign_out.href, "/oauth2/sign_out")
        self.assertEqual(sign_out.children, "Sign out (switch account)")
        self.assertEqual(manage_permissions.href, "https://myapps.microsoft.com/")
        self.assertEqual(manage_permissions.target, "_blank")
        self.assertEqual(manage_permissions.rel, "noopener noreferrer")
