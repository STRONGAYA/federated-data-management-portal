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
            layout_plausibility,
        )
        cls.pages = (landing, layout_availability, layout_completeness, layout_plausibility)

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
