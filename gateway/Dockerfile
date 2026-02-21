FROM python:3.12-slim

WORKDIR /app

# Install uv for fast dependency management
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy everything needed for install
COPY pyproject.toml .
COPY src/ src/
COPY alembic/ alembic/
COPY alembic.ini .

# Install the package
RUN uv pip install --system "."

EXPOSE 8000

CMD ["uvicorn", "mcpfarm_gateway.main:app", "--host", "0.0.0.0", "--port", "8000"]
