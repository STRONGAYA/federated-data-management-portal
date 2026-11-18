# Federated Data Management Portal

This repository contains a Dash/Plotly dashboard for federated data management summaries.

The application is static: it reads local JSON files and does not contact external services.
For a hosted deployment, provide the schema and dashboard data as a Docker volume and run the
application with Docker Compose.

A demo can be seen below or found in the form of an mp4 file in the `example_data/` directory.
The version of the deployed portal is shown in the footer of every page. Releases are tagged `v*`.


https://github.com/user-attachments/assets/6a0a236c-e856-4fde-9f2e-331bc5b36da6

## How was this work funded?

This work and the associated scientific publication ([https://doi.org/10.3389/fams.2026.1981705](https://doi.org/10.3389/fams.2026.1981705)) were predominantly
supported by the European Union's Horizon 2020 research and innovation programme through _The STRONG-AYA Initiative_
(Grant agreement ID: 101057482).

## Data files

The Compose setup expects two files outside the repository:

```text
data/
  schema.jsonld
  dashboard.json
```

`schema.jsonld` contains the semantic schema used by the dashboard, in JSON-LD format. It must
include the schema metadata consumed by the callbacks, including `schema.prefixes` and
`schema.variables` with camelCase field names (`dataType`, `valueMapping`, `schemaReconstruction`).

`dashboard.json` contains the dashboard data consumed by the Dash callbacks. Top-level keys must be
ISO timestamps for the generated dashboard snapshot; each snapshot is one bar on the horizontal
axis of the data availability over time chart, so loading multiple snapshots compares the
available data between those moments:

```json
{
  "2026-01-01T00:00:00": {
    "Organisation name": {
      "country": "Country",
      "sample_size": 123,
      "categorical": "{\"variable\":{},\"value\":{},\"count\":{}}",
      "numerical": "{\"variable\":{},\"statistic\":{},\"value\":{}}"
    }
  }
}
```

In addition, a reserved top-level `aggregate` key may hold the results of the central
(aggregating) task of the "Descriptive statistics" Vantage6 algorithm. It is keyed by ISO
timestamp as well and feeds the data exploration page, which draws the distribution of each
continuous variable from the federated quartiles (q1, median, q3) and the derived IQR.
The central result has `min` and `max` removed by the algorithm, so the figure shows only
what the quartiles state: the Q1–Q3 range holds the middle 50% of patients in a typical
organisation. That range is drawn as a solid horizontal whisker with caps at Q1 and Q3, the Q1/Q2/Q3 values
labelled in the plot, and the median marked with a short dashed tick; no density curve is drawn,
because the quartiles do not record the shape or peak of the distribution. The lowest and
highest 25% (a further 25% on each side) are shown as grey dashed extensions outside Q1–Q3;
their actual range is not shared (minimum, maximum and raw values are removed), so their
extent is inferred, not recorded. Below the whisker, one strip row on a single vertical axis shows
each organisation's own Q1–median–Q3 whisker in the organisation's own colour, and beneath those
one whisker per country (estimated by combining that country's organisations' quartiles weighted
by their counts — an estimate, not a recorded value), with a subtle dotted separator and
'Organisations'/'Countries' labels between the two groups. The categorical tile has two sections, each with its own label, visualisation selector
and download button: the top one over the selected organisations, and below a subtle dotted
line one per country (counts or proportions, or a CSV table) showing the variable's values
within each country (e.g. males/females per country) over the selected organisations. The page also warns when more than a quarter of the
variation lies between organisations (computed from `std` versus `adjusted std`) or when
organisation medians spread wider than the federated IQR; the stats line and the warnings
prefer `adjusted std` (the SD of all patients combined) over `std` (the within-organisation
SD) when the central result carries both:

```json
{
  "aggregate": {
    "2026-01-01T00:00:00": {
      "categorical": "{\"variable\":{},\"value\":{},\"count\":{}}",
      "numerical": "{\"variable\":{},\"statistic\":{},\"value\":{}}"
    }
  }
}
```

The vantage6-native key names `categorical_general_statistics` and
`numerical_general_statistics` are accepted as aliases for `categorical` and `numerical`.

Example versions of both files are included in `example_data/` and can be used to run the
dashboard locally:

```bash
SCHEMA_FILE_PATH=example_data/schema.jsonld \
DASHBOARD_DATA_FILE_PATH=example_data/dashboard.json \
uv run python -m federated_data_management_portal.main
```

## Running With Docker Compose

Create or mount the external `data/` directory, then run:

```bash
docker compose up --build
```

The dashboard will be available at `http://localhost:8050`.

The default Compose file mounts `./data` to `/data` and sets:

```text
SCHEMA_FILE_PATH=/data/schema.jsonld
DASHBOARD_DATA_FILE_PATH=/data/dashboard.json
```

## Running Locally

Use Python 3.12:

```bash
python -m venv .venv
source .venv/bin/activate
uv sync --no-dev
SCHEMA_FILE_PATH=/path/to/schema.jsonld \
DASHBOARD_DATA_FILE_PATH=/path/to/dashboard.json \
uv run python -m federated_data_management_portal.main
```

Both `SCHEMA_FILE_PATH` and `DASHBOARD_DATA_FILE_PATH` are required.

## Tests

Run the test suite with the dev dependencies:

```bash
uv sync
uv run --group dev pytest tests/
```

## Dependencies

Runtime dependencies are pinned in `pyproject.toml`.

The default install contains only the static dashboard stack:

- Dash
- dash-bootstrap-components
- pandas
- Plotly
