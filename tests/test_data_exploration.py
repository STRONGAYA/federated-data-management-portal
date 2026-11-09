import json
import tempfile
import unittest
from pathlib import Path

import numpy as np

from federated_data_management_portal import callbacks
from federated_data_management_portal.main import (
    load_static_dashboard_data,
    split_aggregate_section,
)

EXAMPLE_DATA = Path(__file__).resolve().parent.parent / "example_data"


def categorical_stats(variables, values, counts):
    return json.dumps({
        "variable": dict(enumerate(variables)),
        "value": dict(enumerate(values)),
        "count": dict(enumerate(counts)),
    })


def numerical_stats(variables, statistics, values):
    return json.dumps({
        "variable": dict(enumerate(variables)),
        "statistic": dict(enumerate(statistics)),
        "value": dict(enumerate(values)),
    })


def organisation(categorical="{}", numerical="{}", **extra):
    data = {
        "country": "Testland",
        "categorical": categorical,
        "numerical": numerical,
    }
    data.update(extra)
    return data


def dashboard_data(organisations):
    return {"2026-01-01T00:00:00": organisations}


def aggregate_data(numerical="{}", categorical="{}", timestamp="2026-01-01T00:00:00"):
    return {timestamp: {"numerical": numerical, "categorical": categorical}}


SCHEMA = {
    "schema": {
        "prefixes": {"ncit": "http://ncicb.nci.nih.gov/xml/owl/EVS/Thesaurus.owl#"},
        "variables": {
            "biological_sex": {
                "class": "ncit:C28421",
                "dataType": "categorical",
                "valueMapping": {"terms": {
                    "male": {"targetClass": "ncit:C20197"},
                    "female": {"targetClass": "ncit:C16576"},
                    "missing_or_unspecified": {"targetClass": "ncit:C54031"},
                }},
            },
            "age_at_diagnosis": {"class": "ncit:C156420", "dataType": "continuous"},
            "tumour_location": {"class": "ncit:C3263", "dataType": "categorical"},
        },
    }
}

SEX_CATEGORICAL = categorical_stats(
    ["ncit:C28421", "ncit:C28421", "ncit:C28421", "ncit:C28421"],
    ["ncit:C20197", "ncit:C16576", "nan", "outliers"],
    [10, 5, 2, 0],
)

CANCER_CATEGORICAL = categorical_stats(
    ["ncit:C3263", "ncit:C3263", "ncit:C3263"],
    ["C50.9", "C34.9", "nan"],
    [7, 3, 1],
)

AGGREGATE_NUMERICAL = numerical_stats(
    ["ncit:C156420"] * 6,
    ["q1", "median", "q3", "mean", "std", "count"],
    [30.0, 32.5, 38.75, 34.5, 7.8, 18.0],
)


class SplitAggregateSectionTests(unittest.TestCase):
    def test_split_removes_the_reserved_key_from_the_snapshots(self):
        full = {
            "2026-01-01T00:00:00": {"Org": organisation()},
            "aggregate": aggregate_data(),
        }

        snapshots, aggregate = split_aggregate_section(full)

        self.assertEqual(list(snapshots.keys()), ["2026-01-01T00:00:00"])
        self.assertEqual(list(aggregate.keys()), ["2026-01-01T00:00:00"])

    def test_split_defaults_to_an_empty_aggregate_section(self):
        snapshots, aggregate = split_aggregate_section(dashboard_data({"Org": organisation()}))

        self.assertEqual(list(snapshots.keys()), ["2026-01-01T00:00:00"])
        self.assertEqual(aggregate, {})

    def test_loader_accepts_the_aggregate_section(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "dashboard.json"
            path.write_text(json.dumps({
                "2026-01-01T00:00:00": {"Org": organisation()},
                "aggregate": aggregate_data(),
            }), encoding="utf-8")

            data = load_static_dashboard_data(path)

        self.assertIn("aggregate", data)

    def test_loader_rejects_non_timestamp_keys_inside_the_aggregate_section(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "dashboard.json"
            path.write_text(json.dumps({
                "2026-01-01T00:00:00": {"Org": organisation()},
                "aggregate": {"not-a-timestamp": {}},
            }), encoding="utf-8")

            with self.assertRaises(SystemExit):
                load_static_dashboard_data(path)

    def test_loader_still_rejects_bad_top_level_keys(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "dashboard.json"
            path.write_text(json.dumps({"not-a-timestamp": {}}), encoding="utf-8")

            with self.assertRaises(SystemExit):
                load_static_dashboard_data(path)


class LoadAggregateStatsTests(unittest.TestCase):
    def test_uses_the_latest_aggregate_snapshot(self):
        aggregate = {
            "2025-12-01T00:00:00": {"numerical": numerical_stats(["ncit:C156420"], ["count"], [1.0])},
            "2026-01-01T00:00:00": {"numerical": AGGREGATE_NUMERICAL},
        }

        _, numerical = callbacks.load_aggregate_stats(aggregate)

        self.assertEqual(set(numerical["statistic"]), {"q1", "median", "q3", "mean", "std", "count"})

    def test_accepts_the_vantage6_native_central_keys(self):
        aggregate = {"2026-01-01T00:00:00": {
            "numerical_general_statistics": AGGREGATE_NUMERICAL,
            "categorical_general_statistics": SEX_CATEGORICAL,
        }}

        categorical, numerical = callbacks.load_aggregate_stats(aggregate)

        self.assertEqual(len(numerical), 6)
        self.assertEqual(len(categorical), 4)

    def test_returns_empty_frames_without_aggregate_data(self):
        categorical, numerical = callbacks.load_aggregate_stats({})

        self.assertEqual(len(categorical), 0)
        self.assertEqual(len(numerical), 0)


class DistributionCurveFigureTests(unittest.TestCase):
    @staticmethod
    def curve_area(trace):
        x, y = np.asarray(trace.x), np.asarray(trace.y)
        return float(np.sum((y[:-1] + y[1:]) / 2 * np.diff(x)))

    def test_curve_is_a_density_on_a_dense_evenly_spaced_grid(self):
        figure = callbacks.generate_distribution_curve_figure(
            aggregate_data(numerical=AGGREGATE_NUMERICAL), "ncit:C156420", SCHEMA)

        trace = figure.data[0]
        self.assertEqual(trace.type, "scatter")
        self.assertEqual(trace.fill, "tozeroy")
        self.assertEqual(len(trace.x), callbacks._CURVE_GRID_POINTS)
        diffs = np.diff(trace.x)
        self.assertTrue(np.allclose(diffs, diffs[0]))
        # the curve is a proper density: it integrates to ~1
        self.assertAlmostEqual(self.curve_area(trace), 1.0, places=2)
        self.assertEqual(figure.layout.title.text, "Federated distribution of Age At Diagnosis")

    def test_symmetric_quartiles_peak_at_the_median(self):
        numerical = numerical_stats(["ncit:C156420"] * 3, ["q1", "median", "q3"], [30.0, 32.5, 35.0])
        figure = callbacks.generate_distribution_curve_figure(
            aggregate_data(numerical=numerical), "ncit:C156420", SCHEMA)

        trace = figure.data[0]
        peak_x = trace.x[int(np.argmax(trace.y))]
        self.assertAlmostEqual(peak_x, 32.5, places=1)

    def test_right_skewed_positive_quartiles_are_log_transformed(self):
        figure = callbacks.generate_distribution_curve_figure(
            aggregate_data(numerical=AGGREGATE_NUMERICAL), "ncit:C156420", SCHEMA)

        trace = figure.data[0]
        peak_x = trace.x[int(np.argmax(trace.y))]
        # the log-normal mode lies below the median
        self.assertLess(peak_x, 32.5)
        self.assertAlmostEqual(self.curve_area(trace), 1.0, places=2)

    def test_iqr_band_and_median_are_marked(self):
        figure = callbacks.generate_distribution_curve_figure(
            aggregate_data(numerical=AGGREGATE_NUMERICAL), "ncit:C156420", SCHEMA)

        shapes = {shape.type: shape for shape in figure.layout.shapes}
        self.assertEqual(shapes["rect"].x0, 30.0)
        self.assertEqual(shapes["rect"].x1, 38.75)
        self.assertEqual(shapes["line"].x0, 32.5)

    def test_the_figure_keeps_the_graph_space_free_of_numbers(self):
        figure = callbacks.generate_distribution_curve_figure(
            aggregate_data(numerical=AGGREGATE_NUMERICAL), "ncit:C156420", SCHEMA)

        self.assertEqual(len(figure.layout.annotations), 0)


class FormatDistributionStatsTests(unittest.TestCase):
    def test_summarises_the_quartiles_and_transform(self):
        text = callbacks.format_distribution_stats(
            aggregate_data(numerical=AGGREGATE_NUMERICAL), "ncit:C156420")

        self.assertIn("Q1: 30.00", text)
        self.assertIn("Median: 32.50", text)
        self.assertIn("Q3: 38.75", text)
        self.assertIn("IQR: 8.75", text)
        self.assertIn("n: 18", text)
        self.assertIn("(log-transformed)", text)

    def test_symmetric_quartiles_are_marked_normal(self):
        numerical = numerical_stats(["ncit:C156420"] * 3, ["q1", "median", "q3"], [30.0, 32.5, 35.0])
        text = callbacks.format_distribution_stats(aggregate_data(numerical=numerical), "ncit:C156420")

        self.assertIn("(normal)", text)

    def test_returns_empty_string_without_quartiles(self):
        self.assertEqual(callbacks.format_distribution_stats({}, "ncit:C156420"), "")
        self.assertEqual(callbacks.format_distribution_stats(aggregate_data(), None), "")

    def test_missing_aggregate_section_renders_an_annotation(self):
        figure = callbacks.generate_distribution_curve_figure({}, "ncit:C156420", SCHEMA)

        self.assertEqual(len(figure.data), 0)
        self.assertIn("No central aggregate result available", figure.layout.annotations[0].text)

    def test_missing_variable_renders_an_annotation(self):
        figure = callbacks.generate_distribution_curve_figure(
            aggregate_data(numerical=AGGREGATE_NUMERICAL), None, SCHEMA)

        self.assertIn("Select a variable", figure.layout.annotations[0].text)

    def test_variable_without_quartiles_renders_an_annotation(self):
        numerical = numerical_stats(["ncit:C156420", "ncit:C156420"], ["mean", "count"], [34.5, 18.0])
        figure = callbacks.generate_distribution_curve_figure(
            aggregate_data(numerical=numerical), "ncit:C156420", SCHEMA)

        self.assertIn("No quartile statistics available", figure.layout.annotations[0].text)


class CategoricalDonutTests(unittest.TestCase):
    def test_counts_are_summed_over_the_selected_organisations(self):
        data = dashboard_data({
            "Org A": organisation(categorical=SEX_CATEGORICAL),
            "Org B": organisation(categorical=categorical_stats(
                ["ncit:C28421", "ncit:C28421"], ["ncit:C20197", "ncit:C16576"], [4, 9])),
        })

        figure = callbacks.generate_categorical_donut(data, ["Org A", "Org B"], "biological_sex", SCHEMA)

        labels = list(figure.data[0].labels)
        values = list(figure.data[0].values)
        # valueMapping labels, sorted by count descending; 'outliers' excluded, 'nan' shown as Missing
        self.assertEqual(labels, ["Male", "Female", "Missing"])
        self.assertEqual(values, [14, 14, 2])

    def test_subset_selection_only_counts_the_selected_organisations(self):
        data = dashboard_data({
            "Org A": organisation(categorical=SEX_CATEGORICAL),
            "Org B": organisation(categorical=categorical_stats(
                ["ncit:C28421"], ["ncit:C20197"], [100])),
        })

        figure = callbacks.generate_categorical_donut(data, ["Org A"], "biological_sex", SCHEMA)

        self.assertEqual(list(figure.data[0].values), [10, 5, 2])

    def test_no_selection_renders_an_annotation(self):
        figure = callbacks.generate_categorical_donut(
            dashboard_data({"Org A": organisation(categorical=SEX_CATEGORICAL)}), [], "biological_sex", SCHEMA)

        self.assertIn("Select an organisation", figure.layout.annotations[0].text)


class CancerGroupDonutTests(unittest.TestCase):
    def test_icd10_codes_are_binned_into_donut_sectors_with_descriptions(self):
        data = dashboard_data({
            "Org A": organisation(categorical=CANCER_CATEGORICAL),
            "Org B": organisation(categorical=categorical_stats(
                ["ncit:C3263", "ncit:C3263"], ["C50.9", "C18.7"], [3, 2])),
        })

        figure = callbacks.generate_cancer_group_donut(data, ["Org A", "Org B"], SCHEMA)

        self.assertEqual(figure.data[0].type, "pie")
        labels = list(figure.data[0].labels)
        values = list(figure.data[0].values)
        self.assertIn("C50-C50 - Malignant neoplasm of breast", labels)
        self.assertIn("C30-C39 - Malignant neoplasms of respiratory and intrathoracic organs", labels)
        self.assertIn("C15-C26 - Malignant neoplasms of digestive organs", labels)
        self.assertEqual(dict(zip(labels, values))["C50-C50 - Malignant neoplasm of breast"], 10)
        # largest sector first
        self.assertEqual(values, sorted(values, reverse=True))

    def test_non_icd10_variables_are_not_binned(self):
        data = dashboard_data({"Org A": organisation(categorical=SEX_CATEGORICAL)})

        figure = callbacks.generate_cancer_group_donut(data, ["Org A"], SCHEMA)

        self.assertIn("No ICD-10 coded cancer types", figure.layout.annotations[0].text)

    def test_no_selection_renders_an_annotation(self):
        data = dashboard_data({"Org A": organisation(categorical=CANCER_CATEGORICAL)})

        figure = callbacks.generate_cancer_group_donut(data, [], SCHEMA)

        self.assertIn("Select an organisation", figure.layout.annotations[0].text)

    def test_detect_icd10_variables_ignores_plain_categorical_variables(self):
        import pandas as pd
        frame = pd.DataFrame(json.loads(SEX_CATEGORICAL))

        self.assertEqual(callbacks.detect_icd10_variables(frame), [])


class ExampleDataExplorationTests(unittest.TestCase):
    def setUp(self):
        raw = load_static_dashboard_data(EXAMPLE_DATA / "dashboard.json")
        self.dashboard_data, self.aggregate_data = split_aggregate_section(raw)
        with (EXAMPLE_DATA / "schema.jsonld").open(encoding="utf-8") as f:
            self.schema = json.load(f)

    def test_distribution_curve_renders_for_the_example_aggregate(self):
        figure = callbacks.generate_distribution_curve_figure(
            self.aggregate_data, "ncit:C156420", self.schema)

        trace = figure.data[0]
        self.assertEqual(len(trace.x), callbacks._CURVE_GRID_POINTS)
        x, y = np.asarray(trace.x), np.asarray(trace.y)
        area = float(np.sum((y[:-1] + y[1:]) / 2 * np.diff(x)))
        self.assertAlmostEqual(area, 1.0, places=2)
        shapes = {shape.type: shape for shape in figure.layout.shapes}
        self.assertEqual(shapes["rect"].x0, 29.9)
        self.assertEqual(shapes["rect"].x1, 37.1)

    def test_sex_donut_sums_the_latest_snapshot(self):
        orgs = sorted(self.dashboard_data["2026-01-01T00:00:00"].keys())
        figure = callbacks.generate_categorical_donut(
            self.dashboard_data, orgs, "biological_sex", self.schema)

        labels = list(figure.data[0].labels)
        values = list(figure.data[0].values)
        self.assertEqual(labels[0], "Male")
        self.assertEqual(values[0], 31)
        self.assertEqual(labels[1], "Female")
        self.assertEqual(values[1], 18)

    def test_cancer_donut_groups_the_example_icd10_codes(self):
        orgs = sorted(self.dashboard_data["2026-01-01T00:00:00"].keys())
        figure = callbacks.generate_cancer_group_donut(self.dashboard_data, orgs, self.schema)

        counts = dict(zip(figure.data[0].labels, figure.data[0].values))
        self.assertEqual(counts["C50-C50 - Malignant neoplasm of breast"], 20)
        self.assertEqual(counts["C30-C39 - Malignant neoplasms of respiratory and intrathoracic organs"], 15)
        # C18.7 and C25.9 both fall in the C15-C26 digestive organs block
        self.assertEqual(counts["C15-C26 - Malignant neoplasms of digestive organs"], 6)
        self.assertEqual(counts["C60-C63 - Malignant neoplasms of male genital organs"], 3)


if __name__ == "__main__":
    unittest.main()
