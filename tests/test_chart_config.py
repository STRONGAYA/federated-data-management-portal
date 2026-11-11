import json
import tempfile
import unittest
from pathlib import Path

from dash import dcc

from federated_data_management_portal.main import Dashboard


def find_graphs(component):
    """Yield every dcc.Graph in a component tree, recursing through children."""
    if isinstance(component, dcc.Graph):
        yield component

    children = getattr(component, "children", None)
    if children is None:
        return
    if isinstance(children, (list, tuple)):
        for child in children:
            yield from find_graphs(child)
    else:
        yield from find_graphs(children)


class ChartHoverTests(unittest.TestCase):
    def test_default_template_disables_the_hover_crosshair(self):
        import plotly.io as pio

        import federated_data_management_portal.main  # noqa: F401  (sets the default template)

        template = pio.templates[pio.templates.default]
        self.assertIs(template.layout.dragmode, False)
        self.assertIs(template.layout.xaxis.showspikes, False)
        self.assertIs(template.layout.yaxis.showspikes, False)


    def test_every_figure_disables_the_crosshair_at_layout_level(self):
        import json as _json
        from pathlib import Path as _Path

        from federated_data_management_portal import callbacks

        example = _Path(__file__).resolve().parent.parent / "example_data"
        data = _json.loads((example / "dashboard.json").read_text())
        snapshots = {k: v for k, v in data.items() if k != "aggregate"}
        aggregate = data["aggregate"]
        schema = _json.loads((example / "schema.jsonld").read_text())
        orgs = sorted(snapshots["2026-01-01T00:00:00"].keys())

        figures = [
            callbacks.generate_donut_chart(snapshots, chart_domain="availability", chart_type="organisation"),
            callbacks.generate_sample_size_over_time_chart(snapshots),
            callbacks.generate_sample_size_horizontal_bar(snapshots),
            callbacks.generate_variable_bar_chart(snapshots, domain="completeness", semantic_map_data=schema),
            callbacks.generate_distribution_curve_figure(aggregate, "ncit:C156420", schema),
            callbacks.generate_categorical_pie_figure(snapshots, orgs, "biological_sex", schema),
            callbacks.generate_categorical_bar_figure(snapshots, orgs, "biological_sex", schema),
        ]
        for figure in figures:
            if isinstance(figure, dict):
                self.assertIs(figure["layout"]["dragmode"], False, figure)
                self.assertIs(figure["layout"]["hovermode"], "closest", figure)
            else:
                self.assertIs(figure.layout.dragmode, False, figure)
                self.assertIs(figure.layout.hovermode, "closest", figure)

    def test_served_figures_carry_the_template(self):
        import plotly.io as pio

        import federated_data_management_portal.main  # noqa: F401
        from federated_data_management_portal import callbacks

        figure = callbacks.generate_donut_chart({"2026-01-01T00:00:00": {}}, chart_domain="availability")
        template = figure.to_plotly_json()["layout"]["template"]
        self.assertIs(template["layout"]["dragmode"], False)


class ChartModeBarTests(unittest.TestCase):
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

    def graphs(self):
        return [graph for page in self.pages for graph in find_graphs(page.layout)]

    def test_every_chart_shows_only_the_download_button(self):
        graphs = self.graphs()

        self.assertGreater(len(graphs), 0)
        for graph in graphs:
            self.assertEqual(graph.config.get("modeBarButtons"), [["toImage"]], graph.id)
            self.assertIs(graph.config.get("displayModeBar"), True, graph.id)
            self.assertIs(graph.config.get("displaylogo"), False, graph.id)

    def test_every_chart_has_a_download_filename(self):
        for graph in self.graphs():
            self.assertIn("filename", graph.config.get("toImageButtonOptions", {}), graph.id)


if __name__ == "__main__":
    unittest.main()
