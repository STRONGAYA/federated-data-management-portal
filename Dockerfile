FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
# uv creates the project virtual environment at /app/.venv by default.
ENV PATH="/app/.venv/bin:$PATH"

# Copy a pinned uv binary from Astral's image instead of installing it at build time.
COPY --from=ghcr.io/astral-sh/uv:0.11.24 /uv /usr/local/bin/uv

COPY pyproject.toml uv.lock README.md LICENSE /app/
COPY src /app/src
# Install exactly the locked dependencies and package the app as a normal wheel.
RUN uv sync --locked --no-dev --no-editable

EXPOSE 8050

CMD ["python", "-m", "federated_data_management_portal.main"]
