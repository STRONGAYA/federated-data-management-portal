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

    def test_keeps_the_example_totals(self):
        self.assertEqual(callbacks.fetch_total_sample_size(self.dashboard_data)[0], "1100")
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

    def test_organisations_keep_their_colour_across_charts(self):
        donut = callbacks.generate_donut_chart(
            self.dashboard_data, chart_domain="availability", chart_type="organisation")
        over_time = callbacks.generate_sample_size_over_time_chart(self.dashboard_data)
        horizontal = callbacks.generate_sample_size_horizontal_bar(self.dashboard_data)

        donut_colours = dict(zip(donut.data[0].labels, donut.data[0].marker.colors))
        over_time_colours = {trace.name: trace.marker.color for trace in over_time.data}
        horizontal_colours = {trace["name"]: trace["marker"]["color"] for trace in horizontal["data"]}

        for org in donut_colours:
            self.assertEqual(donut_colours[org], over_time_colours[org])
            self.assertEqual(donut_colours[org], horizontal_colours[org])

    def test_country_donuts_keep_default_sector_colours(self):
        donut = callbacks.generate_donut_chart(
            self.dashboard_data, chart_domain="availability", chart_type="country")

        self.assertIsNone(donut.data[0].marker.colors)

    def test_charts_fill_their_container(self):
        donut = callbacks.generate_donut_chart(self.dashboard_data, chart_domain="availability")
        bar = callbacks.generate_variable_bar_chart(
            self.dashboard_data, domain="completeness", semantic_map_data=self.schema)
        over_time = callbacks.generate_sample_size_over_time_chart(self.dashboard_data)
        horizontal = callbacks.generate_sample_size_horizontal_bar(self.dashboard_data)

        for figure in (donut, bar, over_time):
            self.assertIsNone(figure.layout.width)
        self.assertNotIn("width", horizontal["layout"])

    def test_charts_have_transparent_backgrounds(self):
        donut = callbacks.generate_donut_chart(self.dashboard_data, chart_domain="availability")
        bar = callbacks.generate_variable_bar_chart(
            self.dashboard_data, domain="completeness", semantic_map_data=self.schema)
        over_time = callbacks.generate_sample_size_over_time_chart(self.dashboard_data)
        horizontal = callbacks.generate_sample_size_horizontal_bar(self.dashboard_data)

        for figure in (donut, bar, over_time):
            self.assertEqual(figure.layout.paper_bgcolor, "rgba(0,0,0,0)")
            self.assertEqual(figure.layout.plot_bgcolor, "rgba(0,0,0,0)")
        self.assertEqual(horizontal["layout"]["paper_bgcolor"], "rgba(0,0,0,0)")
        self.assertEqual(horizontal["layout"]["plot_bgcolor"], "rgba(0,0,0,0)")

    def test_over_time_chart_renders_all_snapshots(self):
        figure = callbacks.generate_sample_size_over_time_chart(self.dashboard_data)

        for trace in figure.data:
            self.assertEqual(len(trace.x), 2)
        self.assertEqual(
            [annotation.text for annotation in figure.layout.annotations],
            ["800", "1,100"],
        )

    def test_over_time_chart_handles_a_single_snapshot(self):
        single = {"2026-01-01T00:00:00": self.dashboard_data["2026-01-01T00:00:00"]}

        figure = callbacks.generate_sample_size_over_time_chart(single)

        for trace in figure.data:
            self.assertEqual(len(trace.x), 1)

    def test_over_time_chart_handles_empty_data(self):
        figure = callbacks.generate_sample_size_over_time_chart({})

        self.assertEqual(len(figure.data), 0)


if __name__ == "__main__":
    unittest.main()
