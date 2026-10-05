import math
import unittest
from pathlib import Path

from federated_data_management_portal import callbacks
from federated_data_management_portal.main import (
    load_json_file,
    load_static_dashboard_data,
)

EXAMPLE_DATA = Path(__file__).resolve().parent.parent / "example_data"


class ExampleDataTests(unittest.TestCase):
    def setUp(self):
        self.dashboard_data = load_static_dashboard_data(EXAMPLE_DATA / "dashboard.json")
        self.schema = load_json_file(EXAMPLE_DATA / "schema.jsonld")

    def assert_no_nan(self, values):
        for value in values:
            self.assertFalse(
                isinstance(value, float) and math.isnan(value),
                f"chart contains nan: {list(values)}",
            )

    def test_dashboard_data_passes_the_app_loader(self):
        snapshot = self.dashboard_data["2026-01-01T00:00:00"]

        self.assertEqual(
            sorted(snapshot),
            ["Mare Imbrium", "Mare Moscoviense", "Mare Serenitatis"],
        )
        for org_data in snapshot.values():
            self.assertIn("country", org_data)
            self.assertIn("sample_size", org_data)
            self.assertIn("categorical", org_data)
            self.assertIn("numerical", org_data)

    def test_keeps_the_original_example_totals(self):
        self.assertEqual(callbacks.fetch_total_sample_size(self.dashboard_data)[0], "100150")
        self.assertEqual(callbacks.fetch_field_count(self.dashboard_data)[0], "2")

    def test_donut_charts_render_for_every_domain(self):
        for domain in ("availability", "completeness", "plausibility"):
            for chart_type in ("organisation", "country"):
                figure = callbacks.generate_donut_chart(
                    self.dashboard_data, chart_domain=domain, chart_type=chart_type)

                self.assert_no_nan(figure.data[0].values)
                if figure.data[0].customdata:
                    self.assert_no_nan(figure.data[0].customdata)

    def test_variable_bar_charts_render_for_both_domains(self):
        for domain in ("completeness", "plausibility"):
            figure = callbacks.generate_variable_bar_chart(
                self.dashboard_data, domain=domain, semantic_map_data=self.schema)

            self.assertGreater(len(figure.data[0].x), 0)
            for trace in figure.data:
                self.assert_no_nan(tuple(trace.y))

    def test_sample_size_bar_renders(self):
        figure = callbacks.generate_sample_size_horizontal_bar(self.dashboard_data)

        self.assertEqual(len(figure["data"]), 3)


if __name__ == "__main__":
    unittest.main()
