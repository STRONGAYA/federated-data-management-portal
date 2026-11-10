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

        cls.dashboard = Dashboard(schema_path, dashboard_path)

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

    def test_header_uses_the_info_portal_font_awesome_icons(self):
        for page in self.pages:
            rendered = json.dumps(page.layout, default=str)
            for icon in ("fa-linkedin-in", "fa-bluesky", "fa-instagram", "fa-envelope", "fa-chevron-down"):
                self.assertIn(icon, rendered, f"{page.__name__} missing {icon}")

    def test_external_links_are_plain_text_without_an_arrow_icon(self):
        for page in self.pages:
            rendered = json.dumps(page.layout, default=str)
            self.assertNotIn("fa-arrow-up-right-from-square", rendered, page.__name__)
            # screen-reader-only new-tab note stays
            self.assertIn("opens in a new tab", rendered, page.__name__)

    def test_chrome_css_renders_links_without_underline_or_link_colour(self):
        css_path = (Path(__file__).resolve().parent.parent / "src" / "federated_data_management_portal"
                    / "assets" / "info_portal_chrome.css")
        css = css_path.read_text(encoding="utf-8")
        self.assertIn("color: inherit", css)
        self.assertIn("text-decoration: none", css)

    def test_internal_nav_bar_is_removed_from_the_app_layout(self):
        rendered = json.dumps(self.dashboard.App.layout, default=str)
        self.assertNotIn("Missing Data", rendered)

    def test_tab_icon_is_the_info_portal_favicon(self):
        self.assertEqual(self.dashboard.App._favicon, "info-portal/favicon.png")
        favicon = (Path(__file__).resolve().parent.parent / "src" / "federated_data_management_portal"
                   / "assets" / "info-portal" / "favicon.png")
        self.assertTrue(favicon.exists())

    def test_external_links_open_in_a_new_tab(self):
        for page in self.pages:
            rendered = json.dumps(page.layout, default=str)
            # every external (https) link in the chrome carries target=_blank
            self.assertIn("target='_blank'", rendered, page.__name__)
            self.assertIn("rel='noopener noreferrer'", rendered, page.__name__)
            self.assertIn("https://strongaya.eu/", rendered, page.__name__)


if __name__ == "__main__":
    unittest.main()
