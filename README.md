# Federated Data Management Portal

This repository contains a Dash/Plotly dashboard for federated data management summaries.

The application is static: it reads local JSON files and does not contact external services.
For a hosted deployment, provide the schema and dashboard data as a Docker volume and run the
application with Docker Compose.

A demo can be seen below or found in the form of an mp4 file in the `example_data/` directory.

https://github.com/user-attachments/assets/6a0a236c-e856-4fde-9f2e-331bc5b36da6

## Data files

The Compose setup expects two files outside the repository:

```text
data/
  schema.json
  dashboard.json
```

`schema.json` contains the semantic schema used by the dashboard. It must include the schema
metadata consumed by the callbacks, including `prefixes` and `variable_info`.

`dashboard.json` contains the dashboard data consumed by the Dash callbacks. Top-level keys must be
ISO timestamps for the generated dashboard snapshot:

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

## Running With Docker Compose

Create or mount the external `data/` directory, then run:

```bash
docker compose up --build
```

The dashboard will be available at `http://localhost:8050`.

The default Compose file mounts `./data` to `/data` and sets:

```text
SCHEMA_FILE_PATH=/data/schema.json
DASHBOARD_DATA_FILE_PATH=/data/dashboard.json
```

## Running Locally

Use Python 3.12:

```bash
python -m venv .venv
source .venv/bin/activate
uv sync --no-dev
SCHEMA_FILE_PATH=/path/to/schema.json \
DASHBOARD_DATA_FILE_PATH=/path/to/dashboard.json \
uv run python federated-data-management-portal/main.py
```

Both `SCHEMA_FILE_PATH` and `DASHBOARD_DATA_FILE_PATH` are required.

## Dependencies

Runtime dependencies are pinned in `pyproject.toml`.

The default install contains only the static dashboard stack:

- Dash
- dash-bootstrap-components
- pandas
- Plotly
