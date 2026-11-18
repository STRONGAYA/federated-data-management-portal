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


class DistributionFigureTests(unittest.TestCase):
    def test_whisker_spans_the_recorded_iqr_with_caps(self):
        figure = callbacks.generate_distribution_figure(
            aggregate_data(numerical=AGGREGATE_NUMERICAL), "ncit:C156420", SCHEMA)

        trace = figure.data[0]
        self.assertEqual(trace.type, "scatter")
        self.assertEqual(trace.mode, "lines")
        x = np.asarray(trace.x, dtype=float)
        y = np.asarray(trace.y, dtype=float)
        # the whisker line and its caps touch only Q1 and Q3
        self.assertEqual(set(np.round(x[~np.isnan(x)], 9)), {30.0, 38.75})
        self.assertAlmostEqual(float(np.nanmax(y)), 0.68)
        self.assertAlmostEqual(float(np.nanmin(y)), 0.32)
        self.assertEqual(figure.layout.title.text, "Federated distribution of Age At Diagnosis")

    def test_no_density_axis_is_shown(self):
        figure = callbacks.generate_distribution_figure(
            aggregate_data(numerical=AGGREGATE_NUMERICAL), "ncit:C156420", SCHEMA)

        # the quartiles record no shape, so the whisker row hides the y-axis
        self.assertFalse(figure.layout.yaxis.visible)

    def test_whisker_is_drawn_regardless_of_skew(self):
        numerical = numerical_stats(["ncit:C156420"] * 3, ["q1", "median", "q3"], [10.0, 12.0, 30.0])
        figure = callbacks.generate_distribution_figure(
            aggregate_data(numerical=numerical), "ncit:C156420", SCHEMA)

        x = np.asarray(figure.data[0].x, dtype=float)
        self.assertEqual(set(np.round(x[~np.isnan(x)], 9)), {10.0, 30.0})

    def test_outer_quarters_are_grey_dashed_and_marked_as_inferred(self):
        numerical = numerical_stats(
            ["ncit:C156420"] * 3, ["q1", "median", "q3"], [29.9, 32.2, 37.1])
        figure = callbacks.generate_distribution_figure(
            aggregate_data(numerical=numerical), "ncit:C156420", SCHEMA)

        self.assertEqual(len(figure.data), 3)
        tail = figure.data[1]
        self.assertEqual(tail.type, "scatter")
        self.assertEqual(tail.line.dash, "dash")
        x_lo, x_hi = figure.layout.xaxis.range
        x = np.asarray(tail.x, dtype=float)
        y = np.asarray(tail.y, dtype=float)
        left = ~np.isnan(x) & (x <= 29.9)
        right = ~np.isnan(x) & (x >= 37.1)
        self.assertAlmostEqual(float(x[left][0]), x_lo)
        self.assertAlmostEqual(float(x[left][-1]), 29.9)
        self.assertAlmostEqual(float(x[right][0]), 37.1)
        self.assertAlmostEqual(float(x[right][-1]), x_hi)
        # the extensions sit at the whisker height
        self.assertTrue(np.all(y[~np.isnan(y)] == 0.5))
        # hover says the extent is inferred, not recorded
        self.assertIn("inferred", tail.hovertemplate)
        self.assertIn("not shared", tail.hovertemplate)
        # the recorded whisker is solid colour, not dashed grey
        self.assertNotEqual(figure.data[0].line.dash, "dash")

    def test_x_range_covers_quartiles_and_organisations(self):
        descriptive = dashboard_data({
            "Org A": organisation(numerical=numerical_stats(
                ["ncit:C156420"] * 3, ["q1", "median", "q3"], [30.0, 32.5, 38.75])),
            "Org B": organisation(numerical=numerical_stats(
                ["ncit:C156420"] * 3, ["q1", "median", "q3"], [29.0, 31.0, 36.0])),
        })
        figure = callbacks.generate_distribution_figure(
            aggregate_data(numerical=AGGREGATE_NUMERICAL), "ncit:C156420", SCHEMA, descriptive)

        # iqr = 38.75 - 30.0 = 8.75; lo/hi pad the outermost quartiles by a quarter IQR
        x_range = list(figure.layout.xaxis.range)
        self.assertAlmostEqual(x_range[0], 29.0 - 0.25 * 8.75)
        self.assertAlmostEqual(x_range[1], 38.75 + 0.25 * 8.75)

    def test_coinciding_quartiles_render_an_annotation(self):
        numerical = numerical_stats(["ncit:C156420"] * 3, ["q1", "median", "q3"], [30.0, 30.0, 35.0])
        figure = callbacks.generate_distribution_figure(
            aggregate_data(numerical=numerical), "ncit:C156420", SCHEMA)

        self.assertIn("Quartiles coincide", figure.layout.annotations[0].text)

    def test_unordered_quartiles_render_an_annotation(self):
        numerical = numerical_stats(["ncit:C156420"] * 3, ["q1", "median", "q3"], [30.0, 40.0, 35.0])
        figure = callbacks.generate_distribution_figure(
            aggregate_data(numerical=numerical), "ncit:C156420", SCHEMA)

        self.assertIn("not in order", figure.layout.annotations[0].text)

    def test_quartile_values_are_labelled_in_the_plot(self):
        figure = callbacks.generate_distribution_figure(
            aggregate_data(numerical=AGGREGATE_NUMERICAL), "ncit:C156420", SCHEMA)

        labels = figure.data[2]
        self.assertEqual(labels.mode, "text")
        self.assertEqual(list(labels.text), ["Q1: 30.00", "Q2: 32.50", "Q3: 38.75"])
        self.assertEqual(list(labels.x), [30.0, 32.5, 38.75])
        # labels are trace text, so the layout keeps zero annotations
        self.assertEqual(len(figure.layout.annotations), 0)

    def test_organisation_strip(self):
        descriptive = dashboard_data({
            "Org A": organisation(numerical=numerical_stats(
                ["ncit:C156420"] * 4, ["q1", "median", "q3", "count"], [30.0, 32.5, 38.75, 18.0])),
            "Org B": organisation(numerical=numerical_stats(
                ["ncit:C156420"] * 4, ["q1", "median", "q3", "count"], [29.0, 31.0, 36.0, 16.0])),
        })

        figure = callbacks.generate_distribution_figure(
            aggregate_data(numerical=AGGREGATE_NUMERICAL), "ncit:C156420", SCHEMA, descriptive)

        strip_traces = [trace for trace in figure.data if trace.name in ("Org A", "Org B")]
        self.assertEqual(len(strip_traces), 2)
        self.assertTrue(all(trace.yaxis == "y2" for trace in strip_traces))
        # each organisation is drawn as a whisker: line Q1-Q3 with caps and a median tick
        for trace, q1, median, q3 in ((strip_traces[0], 30.0, 32.5, 38.75),
                                      (strip_traces[1], 29.0, 31.0, 36.0)):
            x = np.asarray(trace.x, dtype=float)
            points = x[~np.isnan(x)]
            self.assertAlmostEqual(float(points.min()), q1)
            self.assertAlmostEqual(float(points.max()), q3)
            self.assertIn(median, set(np.round(points, 9)))
        # both organisations share one country here, so the axis also carries it,
        # with an empty gap level between the groups
        self.assertEqual(list(figure.layout.yaxis2.ticktext), ["Testland", "", "Org B", "Org A"])
        # shapes: the median tick on the whisker row plus the group separator
        median_shapes = [shape for shape in figure.layout.shapes if shape.yref == "y"]
        self.assertEqual(len(median_shapes), 1)
        self.assertAlmostEqual(median_shapes[0].y0, 0.32)
        self.assertAlmostEqual(median_shapes[0].y1, 0.68)
        self.assertEqual(len([s for s in figure.layout.shapes if s.yref == "y2"]), 1)

        plain = callbacks.generate_distribution_figure(
            aggregate_data(numerical=AGGREGATE_NUMERICAL), "ncit:C156420", SCHEMA)
        self.assertEqual(len(plain.data), 3)

    def test_median_is_marked_with_a_small_tick(self):
        figure = callbacks.generate_distribution_figure(
            aggregate_data(numerical=AGGREGATE_NUMERICAL), "ncit:C156420", SCHEMA)

        self.assertEqual(len(figure.layout.shapes), 1)
        shape = figure.layout.shapes[0]
        self.assertEqual(shape.type, "line")
        self.assertEqual(shape.x0, 32.5)
        # a short tick at the whisker height, not a full-height line
        self.assertEqual(shape.yref, "y")
        self.assertAlmostEqual(shape.y0, 0.32)
        self.assertAlmostEqual(shape.y1, 0.68)

    def test_the_figure_keeps_the_graph_space_free_of_numbers(self):
        figure = callbacks.generate_distribution_figure(
            aggregate_data(numerical=AGGREGATE_NUMERICAL), "ncit:C156420", SCHEMA)

        self.assertEqual(len(figure.layout.annotations), 0)

    def test_organisations_and_countries_share_one_axis_with_a_separator(self):
        descriptive = dashboard_data({
            "Org A": organisation(country="Testland", numerical=numerical_stats(
                ["ncit:C156420"] * 4, ["q1", "median", "q3", "count"], [30.0, 32.5, 38.75, 18.0])),
            "Org B": organisation(country="Testland", numerical=numerical_stats(
                ["ncit:C156420"] * 4, ["q1", "median", "q3", "count"], [29.0, 31.0, 36.0, 16.0])),
            "Org C": organisation(country="Otherland", numerical=numerical_stats(
                ["ncit:C156420"] * 4, ["q1", "median", "q3", "count"], [20.0, 22.0, 24.0, 10.0])),
        })

        figure = callbacks.generate_distribution_figure(
            aggregate_data(numerical=AGGREGATE_NUMERICAL), "ncit:C156420", SCHEMA, descriptive)

        # all strip whiskers (3 organisations + 2 countries) live on the same y axis
        strip_traces = [trace for trace in figure.data if trace.yaxis == "y2"]
        self.assertEqual(len(strip_traces), 5)
        # one shared vertical axis: organisations on top, an empty gap level,
        # then countries (ticktext is indexed by tick value, i.e. bottom to top)
        self.assertEqual(list(figure.layout.yaxis2.ticktext),
                         ["Testland", "Otherland", "", "Org C", "Org B", "Org A"])
        # a subtle dotted separator exactly between the two groups: the empty
        # level's centre (level 2) is equidistant from the lowest organisation
        # (level 3) and the highest country (level 1)
        separators = [shape for shape in figure.layout.shapes if shape.yref == "y2"]
        self.assertEqual(len(separators), 1)
        self.assertEqual(separators[0].line.dash, "dot")
        self.assertAlmostEqual(separators[0].y0, 2.0)
        self.assertAlmostEqual(separators[0].y0 - 1, 3 - separators[0].y0)  # even spacing
        # 'Organisations' and 'Countries' sit on the same vertical axis, outside
        # the plot area in the right margin (paper x = 1, anchored left)
        labels = {annotation.text: annotation for annotation in figure.layout.annotations}
        self.assertEqual(set(labels), {"Organisations", "Countries"})
        self.assertEqual(labels["Organisations"].x, labels["Countries"].x)
        self.assertEqual(labels["Organisations"].x, 1.0)
        self.assertEqual(labels["Organisations"].xref, "paper")
        self.assertEqual(labels["Organisations"].xanchor, "left")
        self.assertEqual(labels["Organisations"].yref, "y2")
        self.assertEqual(labels["Countries"].yref, "y2")
        self.assertGreaterEqual(figure.layout.margin.r, 100)  # room for the labels
        # the whisker row and the strip row sit directly on top of each other
        row_gap = figure.layout.yaxis.domain[0] - figure.layout.yaxis2.domain[1]
        self.assertLessEqual(abs(row_gap), 0.005)
        # and the row padding is trimmed: little empty space around the whiskers
        self.assertEqual(list(figure.layout.yaxis.range), [0.3, 1])
        n_levels = 6  # 3 organisations + 2 countries + 1 gap level
        self.assertEqual(list(figure.layout.yaxis2.range), [-0.3, n_levels - 0.7])
        # country whiskers carry the estimate note in the hover
        country_trace = [trace for trace in strip_traces if trace.name == "Testland"][0]
        self.assertIn("weighted by their counts", country_trace.hovertemplate)
        self.assertIn("Estimated", country_trace.hovertemplate)
        self.assertIn("not a recorded value", country_trace.hovertemplate)
        for trace in strip_traces:
            x = np.asarray(trace.x, dtype=float)
            points = x[~np.isnan(x)]
            self.assertEqual(len(set(np.round(points, 9))), 3)
        # the x-axis title sits on the strip row
        self.assertIsNone(figure.layout.xaxis.title.text)
        self.assertEqual(figure.layout.xaxis2.title.text, "Age At Diagnosis")


class CountryQuartilesTests(unittest.TestCase):
    def test_organisations_by_country_groups_the_latest_snapshot(self):
        descriptive = dashboard_data({
            "Org B": organisation(country="Testland"),
            "Org A": organisation(country="Testland"),
            "Org C": organisation(country="Otherland"),
        })

        self.assertEqual(callbacks.organisations_by_country(descriptive),
                         {"Otherland": ["Org C"], "Testland": ["Org A", "Org B"]})
        self.assertEqual(callbacks.organisations_by_country({}), {})

    def test_country_quartiles_combine_organisations_weighted_by_count(self):
        descriptive = dashboard_data({
            "Org A": organisation(country="Testland", numerical=numerical_stats(
                ["ncit:C156420"] * 4, ["q1", "median", "q3", "count"], [30.0, 32.5, 38.75, 18.0])),
            "Org B": organisation(country="Testland", numerical=numerical_stats(
                ["ncit:C156420"] * 4, ["q1", "median", "q3", "count"], [29.0, 31.0, 36.0, 16.0])),
            "Org C": organisation(country="Otherland", numerical=numerical_stats(
                ["ncit:C156420"] * 4, ["q1", "median", "q3", "count"], [20.0, 22.0, 24.0, 10.0])),
        })

        countries = callbacks._country_quartiles(descriptive, "ncit:C156420")

        self.assertEqual([c["country"] for c in countries], ["Otherland", "Testland"])
        testland = countries[1]
        self.assertAlmostEqual(testland["q1"], (18 * 30.0 + 16 * 29.0) / 34)
        self.assertAlmostEqual(testland["median"], (18 * 32.5 + 16 * 31.0) / 34)
        self.assertAlmostEqual(testland["q3"], (18 * 38.75 + 16 * 36.0) / 34)
        self.assertEqual(testland["count"], 34.0)
        self.assertEqual(testland["organisations"], 2)
        otherland = countries[0]
        self.assertEqual((otherland["q1"], otherland["median"], otherland["q3"]), (20.0, 22.0, 24.0))

    def test_country_quartiles_fall_back_to_equal_weights_without_counts(self):
        descriptive = dashboard_data({
            "Org A": organisation(country="Testland", numerical=numerical_stats(
                ["ncit:C156420"] * 3, ["q1", "median", "q3"], [30.0, 32.5, 38.75])),
            "Org B": organisation(country="Testland", numerical=numerical_stats(
                ["ncit:C156420"] * 3, ["q1", "median", "q3"], [29.0, 31.0, 36.0])),
        })

        countries = callbacks._country_quartiles(descriptive, "ncit:C156420")

        self.assertEqual(len(countries), 1)
        self.assertAlmostEqual(countries[0]["q1"], 29.5)
        self.assertAlmostEqual(countries[0]["median"], 31.75)
        self.assertAlmostEqual(countries[0]["q3"], 37.375)
        self.assertIsNone(countries[0]["count"])

    def test_country_quartiles_skip_organisations_without_quartiles(self):
        descriptive = dashboard_data({
            "Org A": organisation(country="Testland", numerical=numerical_stats(
                ["ncit:C156420"] * 3, ["q1", "median", "q3"], [30.0, 32.5, 38.75])),
            "Org B": organisation(country="Testland", numerical=numerical_stats(
                ["ncit:C156420"], ["count"], [5.0])),
        })

        countries = callbacks._country_quartiles(descriptive, "ncit:C156420")

        self.assertEqual(len(countries), 1)
        self.assertEqual(countries[0]["organisations"], 1)
        self.assertEqual(callbacks._country_quartiles(descriptive, "ncit:C999"), [])


class FormatDistributionStatsTests(unittest.TestCase):
    def test_summarises_the_quartiles(self):
        text = callbacks.format_distribution_stats(
            aggregate_data(numerical=AGGREGATE_NUMERICAL), "ncit:C156420")

        self.assertIn("Q1: 30.00", text)
        self.assertIn("Median: 32.50", text)
        self.assertIn("Q3: 38.75", text)
        self.assertIn("IQR: 8.75", text)
        self.assertIn("Mean: 34.50", text)
        self.assertIn("SD (within organisations): 7.80", text)
        self.assertIn("n: 18", text)
        self.assertNotIn("log-transformed", text)
        self.assertNotIn("(normal)", text)

    def test_adjusted_std_is_preferred(self):
        numerical = numerical_stats(
            ["ncit:C156420"] * 5, ["q1", "median", "q3", "std", "adjusted std"],
            [30.0, 32.5, 35.0, 3.0, 6.0])
        text = callbacks.format_distribution_stats(aggregate_data(numerical=numerical), "ncit:C156420")

        self.assertIn("SD (all patients): 6.00", text)
        self.assertNotIn("within organisations", text)

    def test_returns_empty_string_without_quartiles(self):
        self.assertEqual(callbacks.format_distribution_stats({}, "ncit:C156420"), "")
        self.assertEqual(callbacks.format_distribution_stats(aggregate_data(), None), "")

    def test_missing_aggregate_section_renders_an_annotation(self):
        figure = callbacks.generate_distribution_figure({}, "ncit:C156420", SCHEMA)

        self.assertEqual(len(figure.data), 0)
        self.assertIn("No central aggregate result available", figure.layout.annotations[0].text)

    def test_missing_variable_renders_an_annotation(self):
        figure = callbacks.generate_distribution_figure(
            aggregate_data(numerical=AGGREGATE_NUMERICAL), None, SCHEMA)

        self.assertIn("Select a variable", figure.layout.annotations[0].text)

    def test_variable_without_quartiles_renders_an_annotation(self):
        numerical = numerical_stats(["ncit:C156420", "ncit:C156420"], ["mean", "count"], [34.5, 18.0])
        figure = callbacks.generate_distribution_figure(
            aggregate_data(numerical=numerical), "ncit:C156420", SCHEMA)

        self.assertIn("No quartile statistics available", figure.layout.annotations[0].text)


class DistributionWarningsTests(unittest.TestCase):
    def test_returns_empty_when_the_figure_cannot_be_drawn(self):
        self.assertEqual(callbacks.distribution_warnings({}, "ncit:C156420"), [])
        self.assertEqual(callbacks.distribution_warnings(
            aggregate_data(numerical=AGGREGATE_NUMERICAL), None), [])
        numerical = numerical_stats(["ncit:C156420"], ["mean"], [34.5])
        self.assertEqual(callbacks.distribution_warnings(
            aggregate_data(numerical=numerical), "ncit:C156420"), [])
        coinciding = numerical_stats(
            ["ncit:C156420"] * 3, ["q1", "median", "q3"], [30.0, 30.0, 35.0])
        self.assertEqual(callbacks.distribution_warnings(
            aggregate_data(numerical=coinciding), "ncit:C156420"), [])

    def test_between_organisation_share_is_reported(self):
        numerical = numerical_stats(
            ["ncit:C156420"] * 5, ["q1", "median", "q3", "std", "adjusted std"],
            [24.0, 26.1, 28.0, 3.17, 6.87])
        warnings = callbacks.distribution_warnings(
            aggregate_data(numerical=numerical), "ncit:C156420")

        self.assertTrue(any("79% of the variation lies between organisations" in warning
                            for warning in warnings))

    def test_small_between_organisation_share_is_silent(self):
        numerical = numerical_stats(
            ["ncit:C156420"] * 5, ["q1", "median", "q3", "std", "adjusted std"],
            [24.0, 26.1, 28.0, 5.0, 5.2])

        self.assertEqual(callbacks.distribution_warnings(
            aggregate_data(numerical=numerical), "ncit:C156420"), [])

    def test_between_organisation_check_needs_both_sds(self):
        numerical = numerical_stats(
            ["ncit:C156420"] * 4, ["q1", "median", "q3", "std"], [24.0, 26.1, 28.0, 3.17])

        self.assertEqual(callbacks.distribution_warnings(
            aggregate_data(numerical=numerical), "ncit:C156420"), [])

    def test_wide_organisation_medians_are_reported(self):
        descriptive = dashboard_data({
            "Org A": organisation(numerical=numerical_stats(
                ["ncit:C156420"] * 3, ["q1", "median", "q3"], [17.0, 19.0, 21.0])),
            "Org B": organisation(numerical=numerical_stats(
                ["ncit:C156420"] * 3, ["q1", "median", "q3"], [31.0, 33.0, 35.0])),
        })
        numerical = numerical_stats(["ncit:C156420"] * 3, ["q1", "median", "q3"], [24.0, 26.1, 28.0])
        warnings = callbacks.distribution_warnings(
            aggregate_data(numerical=numerical), "ncit:C156420", descriptive)

        self.assertTrue(any("Organisation medians range from 19.00 to 33.00" in warning
                            for warning in warnings))


class CategoricalValueCountsTests(unittest.TestCase):
    def test_counts_are_summed_over_the_selected_organisations(self):
        data = dashboard_data({
            "Org A": organisation(categorical=SEX_CATEGORICAL),
            "Org B": organisation(categorical=categorical_stats(
                ["ncit:C28421", "ncit:C28421"], ["ncit:C20197", "ncit:C16576"], [4, 9])),
        })

        labels, values = callbacks.categorical_value_counts(
            data, ["Org A", "Org B"], "biological_sex", SCHEMA)

        # valueMapping labels, sorted by count descending; 'outliers' excluded, 'nan' shown as Missing
        self.assertEqual(labels, ["Male", "Female", "Missing"])
        self.assertEqual(values, [14, 14, 2])

    def test_subset_selection_only_counts_the_selected_organisations(self):
        data = dashboard_data({
            "Org A": organisation(categorical=SEX_CATEGORICAL),
            "Org B": organisation(categorical=categorical_stats(
                ["ncit:C28421"], ["ncit:C20197"], [100])),
        })

        _, values = callbacks.categorical_value_counts(data, ["Org A"], "biological_sex", SCHEMA)

        self.assertEqual(values, [10, 5, 2])

    def test_cancer_groups_bin_icd10_codes_into_blocks(self):
        data = dashboard_data({
            "Org A": organisation(categorical=CANCER_CATEGORICAL),
            "Org B": organisation(categorical=categorical_stats(
                ["ncit:C3263", "ncit:C3263"], ["C50.9", "C18.7"], [3, 2])),
        })

        labels, values = callbacks.categorical_value_counts(
            data, ["Org A", "Org B"], callbacks.CANCER_GROUPS_VARIABLE, SCHEMA)

        self.assertEqual(labels[0], "C50-C50 - Malignant neoplasm of breast")
        self.assertEqual(values[0], 10)
        self.assertIn("C30-C39 - Malignant neoplasms of respiratory and intrathoracic organs", labels)
        self.assertIn("C15-C26 - Malignant neoplasms of digestive organs", labels)
        self.assertEqual(values, sorted(values, reverse=True))

    def test_returns_none_without_selection_variable_or_data(self):
        data = dashboard_data({"Org A": organisation(categorical=SEX_CATEGORICAL)})

        self.assertIsNone(callbacks.categorical_value_counts(data, [], "biological_sex", SCHEMA))
        self.assertIsNone(callbacks.categorical_value_counts(data, ["Org A"], None, SCHEMA))
        self.assertIsNone(callbacks.categorical_value_counts(
            dashboard_data({"Org A": organisation(categorical=SEX_CATEGORICAL)}),
            ["Org A"], "tumour_location", SCHEMA))


class CategoricalCountryBreakdownTests(unittest.TestCase):
    def test_counts_are_broken_down_per_country_and_value(self):
        data = dashboard_data({
            "Org A": organisation(country="Testland", categorical=SEX_CATEGORICAL),
            "Org B": organisation(country="Testland", categorical=categorical_stats(
                ["ncit:C28421"], ["ncit:C20197"], [100])),
            "Org C": organisation(country="Otherland", categorical=categorical_stats(
                ["ncit:C28421", "ncit:C28421"], ["ncit:C20197", "ncit:C16576"], [7, 3])),
        })

        countries, categories, counts = callbacks.categorical_country_breakdown(
            data, "biological_sex", SCHEMA)

        # Testland total 117 > Otherland total 10; 'outliers' excluded
        self.assertEqual(countries, ["Testland", "Otherland"])
        self.assertEqual(categories, ["Male", "Female", "Missing"])
        self.assertEqual(counts["Male"], [110, 7])
        self.assertEqual(counts["Female"], [5, 3])
        self.assertEqual(counts["Missing"], [2, 0])

    def test_returns_none_without_variable_or_matching_data(self):
        data = dashboard_data({"Org A": organisation(categorical=SEX_CATEGORICAL)})

        self.assertIsNone(callbacks.categorical_country_breakdown(data, None, SCHEMA))
        self.assertIsNone(callbacks.categorical_country_breakdown({}, "biological_sex", SCHEMA))
        self.assertIsNone(callbacks.categorical_country_breakdown(data, "tumour_location", SCHEMA))

    def test_selection_limits_the_organisations_included(self):
        data = dashboard_data({
            "Org A": organisation(country="Testland", categorical=SEX_CATEGORICAL),
            "Org B": organisation(country="Otherland", categorical=categorical_stats(
                ["ncit:C28421"], ["ncit:C20197"], [100])),
        })

        countries, categories, counts = callbacks.categorical_country_breakdown(
            data, "biological_sex", SCHEMA, selection=["Org A"])

        # only Org A's country appears, with Org A's counts
        self.assertEqual(countries, ["Testland"])
        self.assertEqual(counts["Male"], [10])
        self.assertIsNone(callbacks.categorical_country_breakdown(
            data, "biological_sex", SCHEMA, selection=[]))

    def test_country_breakdown_figure_is_one_stacked_bar_per_country(self):
        data = dashboard_data({
            "Org A": organisation(country="Testland", categorical=SEX_CATEGORICAL),
            "Org B": organisation(country="Otherland", categorical=categorical_stats(
                ["ncit:C28421", "ncit:C28421"], ["ncit:C20197", "ncit:C16576"], [30, 10])),
        })

        figure = callbacks.generate_categorical_country_breakdown_figure(
            data, "biological_sex", SCHEMA)

        self.assertEqual(figure.layout.barmode, "stack")
        # one trace per category value
        self.assertEqual({trace.name for trace in figure.data}, {"Male", "Female", "Missing"})
        self.assertTrue(all(trace.orientation == "h" for trace in figure.data))
        # largest country (Otherland, 40) on top
        self.assertEqual(list(figure.data[0].y), ["Testland", "Otherland"])
        male = [trace for trace in figure.data if trace.name == "Male"][0]
        self.assertEqual(list(male.x), [10, 30])  # aligned with the y order: Testland, Otherland
        # the legend sits centred above the plot, and margin autoexpand grows
        # the top margin to fit it, so it can never overlap the plot or x-axis
        self.assertEqual(figure.layout.legend.y, 1.02)
        self.assertEqual(figure.layout.legend.yanchor, "bottom")
        self.assertEqual(figure.layout.legend.x, 0.5)
        self.assertEqual(figure.layout.legend.xanchor, "center")
        self.assertIs(figure.layout.margin.autoexpand, True)
        self.assertIsNone(figure.layout.margin.t)
        self.assertLessEqual(figure.layout.margin.b, 40)

    def test_country_breakdown_figure_annotations(self):
        data = dashboard_data({"Org A": organisation(categorical=SEX_CATEGORICAL)})

        no_variable = callbacks.generate_categorical_country_breakdown_figure(data, None, SCHEMA)
        self.assertIn("Select a variable", no_variable.layout.annotations[0].text)
        no_data = callbacks.generate_categorical_country_breakdown_figure({}, "biological_sex", SCHEMA)
        self.assertIn("No AYA data available", no_data.layout.annotations[0].text)
        no_selection = callbacks.generate_categorical_country_breakdown_figure(
            data, "biological_sex", SCHEMA, selection=[])
        self.assertIn("Select an organisation", no_selection.layout.annotations[0].text)

    def test_country_breakdown_figure_can_stack_proportions(self):
        data = dashboard_data({
            "Org A": organisation(country="Testland", categorical=SEX_CATEGORICAL),
            "Org B": organisation(country="Otherland", categorical=categorical_stats(
                ["ncit:C28421", "ncit:C28421"], ["ncit:C20197", "ncit:C16576"], [30, 10])),
        })

        figure = callbacks.generate_categorical_country_breakdown_figure(
            data, "biological_sex", SCHEMA, proportions=True)

        self.assertEqual(figure.layout.barmode, "stack")
        self.assertEqual(list(figure.layout.xaxis.range), [0, 1])
        self.assertEqual(figure.layout.xaxis.tickformat, ".0%")
        # each country's segments sum to 1
        totals = {}
        for trace in figure.data:
            for country, value in zip(trace.y, trace.x):
                totals[country] = totals.get(country, 0.0) + value
        self.assertEqual(set(totals), {"Testland", "Otherland"})
        for total in totals.values():
            self.assertAlmostEqual(total, 1.0)

    def test_country_csv_has_a_header_and_quoted_rows(self):
        csv_text = callbacks.format_categorical_country_csv(
            ["Testland", 'Other "land"'], ["Male", "Female"],
            {"Male": [10, 30], "Female": [5, 10]})

        self.assertEqual(csv_text.splitlines(), [
            "country,category,count",
            '"Testland","Male",10',
            '"Testland","Female",5',
            '"Other ""land""","Male",30',
            '"Other ""land""","Female",10',
        ])


class CategoricalFigureTests(unittest.TestCase):
    def test_pie_figure_is_a_donut_without_title(self):
        data = dashboard_data({"Org A": organisation(categorical=SEX_CATEGORICAL)})

        figure = callbacks.generate_categorical_pie_figure(data, ["Org A"], "biological_sex", SCHEMA)

        self.assertEqual(figure.data[0].type, "pie")
        self.assertIsNone(figure.layout.title.text)
        self.assertEqual(list(figure.data[0].labels), ["Male", "Female", "Missing"])
        # the legend sits centred above the plot, and margin autoexpand grows
        # the top margin to fit it, so it can never overlap the chart
        self.assertEqual(figure.layout.legend.y, 1.02)
        self.assertEqual(figure.layout.legend.yanchor, "bottom")
        self.assertEqual(figure.layout.legend.x, 0.5)
        self.assertEqual(figure.layout.legend.xanchor, "center")
        self.assertIs(figure.layout.margin.autoexpand, True)
        self.assertIsNone(figure.layout.margin.t)  # not fixed: plotly sizes it

    def test_bar_figure_is_horizontal_with_the_largest_bar_on_top(self):
        data = dashboard_data({"Org A": organisation(categorical=SEX_CATEGORICAL)})

        figure = callbacks.generate_categorical_bar_figure(data, ["Org A"], "biological_sex", SCHEMA)

        self.assertEqual(figure.data[0].orientation, "h")
        # single series: the y labels name the categories, so no legend
        self.assertIs(figure.data[0].showlegend, False)
        values = list(figure.data[0].x)
        self.assertEqual(values, sorted(values))
        self.assertEqual(list(figure.data[0].y)[-1], "Male")

    def test_no_selection_renders_an_annotation(self):
        data = dashboard_data({"Org A": organisation(categorical=SEX_CATEGORICAL)})

        for figure_fn in (callbacks.generate_categorical_pie_figure,
                          callbacks.generate_categorical_bar_figure):
            figure = figure_fn(data, [], "biological_sex", SCHEMA)
            self.assertIn("Select an organisation", figure.layout.annotations[0].text)


class CategoricalCsvTests(unittest.TestCase):
    def test_csv_has_a_header_and_quoted_rows(self):
        csv_text = callbacks.format_categorical_csv(
            ["Male", 'C50-C50 - "breast"'], [14, 10])

        self.assertEqual(csv_text.splitlines(), [
            "category,count",
            '"Male",14',
            '"C50-C50 - ""breast""",10',
        ])


class Icd10DetectionTests(unittest.TestCase):
    def test_detect_icd10_variables_ignores_plain_categorical_variables(self):
        import pandas as pd
        frame = pd.DataFrame(json.loads(SEX_CATEGORICAL))

        self.assertEqual(callbacks.detect_icd10_variables(frame), [])

    def test_detect_icd10_variables_in_data_finds_cancer_codes(self):
        data = dashboard_data({"Org A": organisation(categorical=CANCER_CATEGORICAL)})

        self.assertEqual(callbacks.detect_icd10_variables_in_data(data), ["ncit:C3263"])
        self.assertEqual(callbacks.detect_icd10_variables_in_data(
            dashboard_data({"Org A": organisation(categorical=SEX_CATEGORICAL)})), [])


class ViewSelectionButtonTests(unittest.TestCase):
    def test_exploration_page_has_the_info_portal_view_button_and_menu(self):
        import json as _json
        import tempfile as _tempfile
        from pathlib import Path as _Path

        from federated_data_management_portal.main import Dashboard
        with _tempfile.TemporaryDirectory() as td:
            _Path(td, "schema.jsonld").write_text("{}")
            _Path(td, "dashboard.json").write_text(_json.dumps({"2026-01-01T00:00:00": {}}))
            Dashboard(_Path(td, "schema.jsonld"), _Path(td, "dashboard.json"))
        import dash
        from federated_data_management_portal.pages import layout_exploration  # noqa: F401

        rendered = _json.dumps(dash.page_registry["pages.layout_exploration"]["layout"], default=str)
        for needle in ("vis-btn", "view-selection-btn", "exploration-view-toggle",
                       "exploration-view-menu", "filter-dropdown", "exploration-view-store",
                       "view-type-indicator", "exploration-csv-download-btn"):
            self.assertIn(needle, rendered)
        # one unified download button (plot + csv) in the per-organisation
        # section, between the tile divider and the chart
        self.assertIn("plot-download-btn", rendered)
        self.assertIn("Download plot", rendered)
        self.assertIn("Download CSV", rendered)
        self.assertLess(rendered.index("tile-divider"),
                        rendered.index("plot-download-btn"))
        self.assertLess(rendered.index("exploration-view-toggle"),
                        rendered.index("exploration-categorical-graph"))

    def test_exploration_page_has_two_categorical_plots_with_labels(self):
        import json as _json
        import tempfile as _tempfile
        from pathlib import Path as _Path

        from federated_data_management_portal.main import Dashboard
        with _tempfile.TemporaryDirectory() as td:
            _Path(td, "schema.jsonld").write_text("{}")
            _Path(td, "dashboard.json").write_text(_json.dumps({"2026-01-01T00:00:00": {}}))
            Dashboard(_Path(td, "schema.jsonld"), _Path(td, "dashboard.json"))
        import dash
        from federated_data_management_portal.pages import layout_exploration  # noqa: F401

        rendered = _json.dumps(dash.page_registry["pages.layout_exploration"]["layout"], default=str)
        self.assertIn("exploration-categorical-graph", rendered)
        self.assertIn("exploration-categorical-graph-country", rendered)
        # each plot carries a small label
        self.assertIn("exploration-plot-label", rendered)
        self.assertIn("Selected organisations", rendered)
        self.assertIn("Per country (selected organisations)", rendered)
        # the org section has its own controls row, label on the left, between
        # the tile divider and the org chart
        self.assertLess(rendered.index("tile-divider"),
                        rendered.index("exploration-view-toggle"))
        self.assertLess(rendered.index("Selected organisations"),
                        rendered.index("exploration-view-toggle"))
        # no country dropdown remains
        self.assertNotIn("exploration-country-dropdown", rendered)
        # the per-country chart sits below the org chart, separated by a subtle
        # dotted line, and has its own view selector and download button
        self.assertLess(rendered.index("exploration-categorical-graph"),
                        rendered.index("exploration-categorical-divider"))
        self.assertLess(rendered.index("exploration-categorical-divider"),
                        rendered.index("exploration-categorical-graph-country"))
        for needle in ("exploration-country-view-toggle", "exploration-country-view-menu",
                       "exploration-country-view-store", "exploration-country-view-bar",
                       "exploration-country-view-percent", "exploration-country-view-csv",
                       "exploration-country-csv-download-btn", "Proportions",
                       "exploration-categorical-country-csv-table"):
            self.assertIn(needle, rendered)
        # the country controls sit below the dotted line, next to the country chart
        self.assertLess(rendered.index("exploration-categorical-divider"),
                        rendered.index("exploration-country-view-toggle"))

    def test_exploration_page_has_the_distribution_warnings_div(self):
        import json as _json
        import tempfile as _tempfile
        from pathlib import Path as _Path

        from federated_data_management_portal.main import Dashboard
        with _tempfile.TemporaryDirectory() as td:
            _Path(td, "schema.jsonld").write_text("{}")
            _Path(td, "dashboard.json").write_text(_json.dumps({"2026-01-01T00:00:00": {}}))
            Dashboard(_Path(td, "schema.jsonld"), _Path(td, "dashboard.json"))
        import dash
        from federated_data_management_portal.pages import layout_exploration  # noqa: F401

        rendered = _json.dumps(dash.page_registry["pages.layout_exploration"]["layout"], default=str)
        self.assertIn("exploration-distribution-warnings", rendered)
        # the warnings div sits between the stats line and the disclaimer
        self.assertLess(rendered.index("exploration-distribution-stats"),
                        rendered.index("exploration-distribution-warnings"))
        self.assertLess(rendered.index("exploration-distribution-warnings"),
                        rendered.index("exploration-distribution-disclaimer"))


class VariableDonutViewTests(unittest.TestCase):
    def test_donut_view_aggregates_the_latest_snapshot(self):
        import json as _json
        from pathlib import Path as _Path

        example = _Path(__file__).resolve().parent.parent / "example_data"
        data = _json.loads((example / "dashboard.json").read_text())
        snapshots = {k: v for k, v in data.items() if k != "aggregate"}

        for domain, first_label in (("completeness", "Complete AYA data points"),
                                    ("plausibility", "Plausible AYA data points")):
            figure = callbacks.generate_variable_donut_chart(snapshots, domain=domain)
            self.assertEqual(figure.data[0].type, "pie")
            self.assertEqual(list(figure.data[0].labels)[0], first_label)
            self.assertEqual(sum(figure.data[0].values), sum(figure.data[0].values))
            self.assertGreater(sum(figure.data[0].values), 0)

    def test_bar_tiles_have_a_view_switch(self):
        import json as _json
        import tempfile as _tempfile
        from pathlib import Path as _Path

        from federated_data_management_portal.main import Dashboard
        with _tempfile.TemporaryDirectory() as td:
            _Path(td, "schema.jsonld").write_text("{}")
            _Path(td, "dashboard.json").write_text(_json.dumps({"2026-01-01T00:00:00": {}}))
            Dashboard(_Path(td, "schema.jsonld"), _Path(td, "dashboard.json"))
        import dash
        for module in ("pages.layout_completeness", "pages.layout_plausibility"):
            rendered = _json.dumps(dash.page_registry[module]["layout"], default=str)
            prefix = module.rsplit("_", 1)[1]
            for needle in (f"{prefix}-view-toggle", f"{prefix}-view-menu", f"{prefix}-view-store",
                           "Select visualisation", "Bar chart", "Pie chart"):
                self.assertIn(needle, rendered, module)


NESTED_SCHEMA = {
    "schema": {
        "prefixes": {"ncit": "http://ncicb.nci.nih.gov/xml/owl/EVS/Thesaurus.owl#"},
        "variables": {
            "eortc_qlq_c30_q1": {
                "class": "ncit:C1", "dataType": "categorical",
                "schemaReconstruction": [
                    {"@type": "schema:ClassNode", "class": "ncit:OUT", "aestheticLabel": "Outcome"},
                    {"@type": "schema:ClassNode", "class": "ncit:QLQC30", "aestheticLabel": "EORTC QLQ-C30"},
                ],
            },
            "eortc_qlq_c30_q2": {
                "class": "ncit:C2", "dataType": "categorical",
                "schemaReconstruction": [
                    {"@type": "schema:ClassNode", "class": "ncit:OUT", "aestheticLabel": "Outcome"},
                    {"@type": "schema:ClassNode", "class": "ncit:QLQC30", "aestheticLabel": "EORTC QLQ-C30"},
                ],
            },
            "biological_sex": {
                "class": "ncit:C28421", "dataType": "categorical",
                "schemaReconstruction": [
                    {"@type": "schema:ClassNode", "class": "ncit:DEM", "aestheticLabel": "Demographic"},
                ],
            },
        },
    }
}


class VariableSelectionDropdownTests(unittest.TestCase):
    def test_categories_come_first_with_nested_labels(self):
        options, var_info = callbacks.build_variable_options(
            NESTED_SCHEMA, {"ncit:C1", "ncit:C2", "ncit:C28421"})

        labels = [o["label"] for o in options]
        # top-level categories first, nested category indented under its parent
        self.assertEqual(labels[0], "Outcome")
        self.assertIn("Outcome > EORTC QLQ-C30", labels)
        self.assertLess(labels.index("Outcome"), labels.index("Outcome > EORTC QLQ-C30"))
        self.assertIn("Demographic", labels)
        # variables come after all categories
        self.assertIn("Biological Sex", labels)
        cat_count = sum(1 for o in options if o["value"].startswith("cat:"))
        self.assertTrue(all(o["value"].startswith("cat:") for o in options[:cat_count]))
        self.assertTrue(all(o["value"].startswith("var:") for o in options[cat_count:]))

    def test_category_selection_expands_to_all_variables_in_it(self):
        _options, var_info = callbacks.build_variable_options(
            NESTED_SCHEMA, {"ncit:C1", "ncit:C2", "ncit:C28421"})

        classes = callbacks.resolve_variable_selection(["cat:ncit:QLQC30"], var_info)
        self.assertEqual(classes, {"ncit:C1", "ncit:C2"})

        classes = callbacks.resolve_variable_selection(["cat:ncit:OUT"], var_info)
        self.assertEqual(classes, {"ncit:C1", "ncit:C2"})

        classes = callbacks.resolve_variable_selection(["var:biological_sex"], var_info)
        self.assertEqual(classes, {"ncit:C28421"})

        self.assertIsNone(callbacks.resolve_variable_selection([], var_info))

    def test_bar_chart_filters_by_selected_classes(self):
        import json as _json
        from pathlib import Path as _Path

        example = _Path(__file__).resolve().parent.parent / "example_data"
        data = _json.loads((example / "dashboard.json").read_text())
        snapshots = {k: v for k, v in data.items() if k != "aggregate"}
        schema = _json.loads((example / "schema.jsonld").read_text())

        full = callbacks.generate_variable_bar_chart(snapshots, domain="completeness", semantic_map_data=schema)
        filtered = callbacks.generate_variable_bar_chart(
            snapshots, domain="completeness", semantic_map_data=schema, selected_classes={"ncit:C28421"})

        self.assertGreater(len(full.data[0].x), len(filtered.data[0].x))
        self.assertEqual(list(filtered.data[0].x), ["Biological Sex"])


class ExampleDataExplorationTests(unittest.TestCase):
    def setUp(self):
        raw = load_static_dashboard_data(EXAMPLE_DATA / "dashboard.json")
        self.dashboard_data, self.aggregate_data = split_aggregate_section(raw)
        with (EXAMPLE_DATA / "schema.jsonld").open(encoding="utf-8") as f:
            self.schema = json.load(f)

    def test_distribution_whisker_renders_for_the_example_aggregate(self):
        figure = callbacks.generate_distribution_figure(
            self.aggregate_data, "ncit:C156420", self.schema)

        trace = figure.data[0]
        self.assertEqual(trace.type, "scatter")
        x = np.asarray(trace.x, dtype=float)
        self.assertEqual(set(np.round(x[~np.isnan(x)], 9)), {29.9, 37.1})
        self.assertFalse(figure.layout.yaxis.visible)
        self.assertEqual(list(figure.data[2].text), ["Q1: 29.90", "Q2: 32.20", "Q3: 37.10"])
        tail_x = np.asarray(figure.data[1].x, dtype=float)
        self.assertAlmostEqual(float(np.nanmin(tail_x)), 28.1)
        self.assertAlmostEqual(float(np.nanmax(tail_x)), 38.9)
        self.assertEqual(len(figure.layout.shapes), 1)
        self.assertEqual(figure.layout.shapes[0].x0, 32.2)

    def test_example_aggregate_produces_no_warnings(self):
        self.assertEqual(
            callbacks.distribution_warnings(self.aggregate_data, "ncit:C156420", self.dashboard_data),
            [])

    def test_example_figure_has_one_strip_trace_per_organisation(self):
        figure = callbacks.generate_distribution_figure(
            self.aggregate_data, "ncit:C156420", self.schema, self.dashboard_data)

        strip_traces = [trace for trace in figure.data if trace.yaxis == "y2"]
        self.assertEqual(len(strip_traces), 5)  # 3 organisations + 2 countries
        self.assertEqual(len([t for t in strip_traces if t.name.startswith("Mare ")]), 3)
        x_range = list(figure.layout.xaxis.range)
        self.assertAlmostEqual(x_range[0], 27.95)
        self.assertAlmostEqual(x_range[1], 40.55)
        # the grey tails span from the padded range ends to Q1 and Q3
        tail_x = np.asarray(figure.data[1].x, dtype=float)
        self.assertAlmostEqual(float(np.nanmin(tail_x)), 27.95)
        self.assertAlmostEqual(float(np.nanmax(tail_x)), 40.55)

    def test_example_figure_has_one_country_whisker_per_country_on_the_shared_axis(self):
        figure = callbacks.generate_distribution_figure(
            self.aggregate_data, "ncit:C156420", self.schema, self.dashboard_data)

        strip_traces = [trace for trace in figure.data if trace.yaxis == "y2"]
        country_names = {"Far side of the Moon", "Near side of the Moon"}
        country_traces = [trace for trace in strip_traces if trace.name in country_names]
        self.assertEqual(len(country_traces), 2)
        self.assertEqual(list(figure.layout.yaxis2.ticktext),
                         ["Near side of the Moon", "Far side of the Moon", "",
                          "Mare Serenitatis", "Mare Moscoviense", "Mare Imbrium"])
        # the country whiskers stay within the padded x-range
        x_range = list(figure.layout.xaxis.range)
        self.assertAlmostEqual(x_range[0], 27.95)
        self.assertAlmostEqual(x_range[1], 40.55)

    def test_sex_counts_sum_the_latest_snapshot(self):
        orgs = sorted(self.dashboard_data["2026-01-01T00:00:00"].keys())
        labels, values = callbacks.categorical_value_counts(
            self.dashboard_data, orgs, "biological_sex", self.schema)

        self.assertEqual(labels[0], "Male")
        self.assertEqual(values[0], 31)
        self.assertEqual(labels[1], "Female")
        self.assertEqual(values[1], 18)

    def test_cancer_groups_count_the_example_icd10_codes(self):
        orgs = sorted(self.dashboard_data["2026-01-01T00:00:00"].keys())
        labels, values = callbacks.categorical_value_counts(
            self.dashboard_data, orgs, callbacks.CANCER_GROUPS_VARIABLE, self.schema)

        counts = dict(zip(labels, values))
        self.assertEqual(counts["C50-C50 - Malignant neoplasm of breast"], 20)
        self.assertEqual(counts["C30-C39 - Malignant neoplasms of respiratory and intrathoracic organs"], 15)
        # C18.7 and C25.9 both fall in the C15-C26 digestive organs block
        self.assertEqual(counts["C15-C26 - Malignant neoplasms of digestive organs"], 6)
        self.assertEqual(counts["C60-C63 - Malignant neoplasms of male genital organs"], 3)


if __name__ == "__main__":
    unittest.main()
