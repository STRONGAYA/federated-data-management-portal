import json
import math
import unittest

from federated_data_management_portal import callbacks


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


HEALTHY_CATEGORICAL = categorical_stats(
    ["ncit:C28421", "ncit:C28421"], ["M", "nan"], [5, 2])
HEALTHY_NUMERICAL = numerical_stats(
    ["ncit:C156420", "ncit:C156420"], ["count", "nan"], [10, 0])


class LoadStatsFrameTests(unittest.TestCase):
    def test_returns_empty_frame_for_missing_statistics(self):
        frame = callbacks._load_stats_frame(None, ["variable", "value", "count"])

        self.assertEqual(len(frame), 0)
        self.assertEqual(list(frame.columns), ["variable", "value", "count"])

    def test_returns_empty_frame_for_malformed_json(self):
        frame = callbacks._load_stats_frame("{not json", ["variable", "value", "count"])

        self.assertEqual(len(frame), 0)

    def test_returns_empty_frame_when_columns_are_missing(self):
        raw = json.dumps({"variable": {"0": "ncit:C28421"}})

        frame = callbacks._load_stats_frame(raw, ["variable", "value", "count"])

        self.assertEqual(len(frame), 0)

    def test_drops_rows_without_variable_identifier(self):
        ragged = json.dumps({
            "variable": {"0": "ncit:C28421"},
            "value": {"0": "M", "1": "nan"},
            "count": {"0": 5, "1": 2},
        })

        categorical, numerical = callbacks._load_organization_stats(
            {"categorical": ragged, "numerical": "{}"})

        self.assertEqual(len(categorical), 1)
        self.assertEqual(len(numerical), 0)


class VariableBarChartTests(unittest.TestCase):
    def assert_no_nan(self, values):
        for value in values:
            self.assertFalse(
                isinstance(value, float) and math.isnan(value),
                f"chart contains nan: {list(values)}",
            )

    def test_renders_when_organisation_has_no_statistics(self):
        data = dashboard_data({
            "Org A": organisation(),
            "Org B": organisation(HEALTHY_CATEGORICAL, HEALTHY_NUMERICAL),
        })

        figure = callbacks.generate_variable_bar_chart(data, domain="completeness")

        for trace in figure.data:
            self.assert_no_nan(tuple(trace.y))

    def test_renders_empty_chart_when_no_statistics_at_all(self):
        data = dashboard_data({"Org A": organisation()})

        figure = callbacks.generate_variable_bar_chart(data, domain="completeness")

        for trace in figure.data:
            self.assertEqual(tuple(trace.y), ())

    def test_accepts_vantage6_statistics_keys(self):
        data = dashboard_data({"Org A": {
            "country": "Testland",
            "categorical_general_partial_statistics": HEALTHY_CATEGORICAL,
            "numerical_general_partial_statistics": HEALTHY_NUMERICAL,
        }})

        figure = callbacks.generate_variable_bar_chart(data, domain="completeness")

        for trace in figure.data:
            self.assertEqual(len(tuple(trace.y)), 2)

    def test_shows_zero_for_variable_without_data_points(self):
        zero_categorical = categorical_stats(["ncit:C43424"], ["M"], [0])
        zero_numerical = numerical_stats(["ncit:C43424"], ["count"], [0])
        data = dashboard_data(
            {"Org A": organisation(zero_categorical, zero_numerical)})

        figure = callbacks.generate_variable_bar_chart(data, domain="completeness")

        for trace in figure.data:
            self.assertEqual(tuple(trace.y), (0.0,))

    def test_plausibility_renders_when_organisation_has_no_statistics(self):
        data = dashboard_data({"Org A": organisation()})

        figure = callbacks.generate_variable_bar_chart(data, domain="plausibility")

        for trace in figure.data:
            self.assertEqual(tuple(trace.y), ())


class DonutChartTests(unittest.TestCase):
    def assert_no_nan(self, values):
        for value in values:
            self.assertFalse(
                isinstance(value, float) and math.isnan(value),
                f"chart contains nan: {list(values)}",
            )

    def test_completeness_reports_zero_for_organisation_without_data(self):
        data = dashboard_data({
            "Org A": organisation(HEALTHY_CATEGORICAL, HEALTHY_NUMERICAL),
            "Org B": organisation(),
        })

        figure = callbacks.generate_donut_chart(
            data, chart_domain="completeness", chart_type="organisation")

        customdata = figure.data[0].customdata
        self.assert_no_nan(customdata)
        self.assertAlmostEqual(customdata[0], 11.8, places=1)
        self.assertEqual(customdata[1], 0.0)

    def test_completeness_country_handles_empty_statistics(self):
        data = dashboard_data({
            "Org A": organisation(HEALTHY_CATEGORICAL, HEALTHY_NUMERICAL),
            "Org B": organisation(),
        })

        figure = callbacks.generate_donut_chart(
            data, chart_domain="completeness", chart_type="country")

        self.assert_no_nan(figure.data[0].customdata)

    def test_plausibility_handles_organisation_without_data(self):
        data = dashboard_data({
            "Org A": organisation(HEALTHY_CATEGORICAL, HEALTHY_NUMERICAL),
            "Org B": organisation(),
        })

        figure = callbacks.generate_donut_chart(
            data, chart_domain="plausibility", chart_type="organisation")

        self.assert_no_nan(figure.data[0].customdata)


if __name__ == "__main__":
    unittest.main()
