import json
import tempfile
import unittest
from pathlib import Path

from federated_data_management_portal.main import Dashboard


class PageChromeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Constructing the app imports and registers the page layouts.
        cls.temp_dir = tempfile.TemporaryDirectory()
        data_dir = Path(cls.temp_dir.name)
        schema_path = data_dir / "schema.jsonld"
        dashboard_path = data_dir / "dashboard.json"
        schema_path.write_text(json.dumps({}), encoding="utf-8")
        dashboard_path.write_text(json.dumps({"2026-01-01T00:00:00": {}}), encoding="utf-8")

        Dashboard(schema_path, dashboard_path)

        from federated_data_management_portal.pages import (
            landing,
            layout_availability,
            layout_completeness,
            layout_exploration,
            layout_plausibility,
        )
        cls.pages = (landing, layout_availability, layout_completeness, layout_exploration, layout_plausibility)

    @classmethod
    def tearDownClass(cls):
        cls.temp_dir.cleanup()

    def test_every_page_uses_the_info_portal_header_and_footer(self):
        for page in self.pages:
            rendered = json.dumps(page.layout, default=str)
            self.assertIn("site-header", rendered, page.__name__)
            self.assertIn("site-footer", rendered, page.__name__)
            self.assertIn("header-topbar", rendered, page.__name__)
            self.assertIn("header-main", rendered, page.__name__)
            self.assertIn("site-nav", rendered, page.__name__)
            self.assertIn("contact-btn", rendered, page.__name__)

    def test_every_page_has_the_internal_use_notice_banner(self):
        for page in self.pages:
            rendered = json.dumps(page.layout, default=str)
            self.assertIn("notice-banner", rendered, page.__name__)
            self.assertIn("internal use only", rendered, page.__name__)

    def test_no_accessibility_controls_are_included(self):
        for page in self.pages:
            rendered = json.dumps(page.layout, default=str)
            self.assertNotIn("accessibility", rendered.lower(), page.__name__)

    def test_footer_keeps_the_portal_version(self):
        for page in self.pages:
            rendered = json.dumps(page.layout, default=str)
            self.assertIn("Version", rendered, page.__name__)


if __name__ == "__main__":
    unittest.main()
