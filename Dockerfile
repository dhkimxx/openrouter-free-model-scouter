FROM python:3.11-slim

# Install uv curl
RUN apt-get update && apt-get install -y --no-install-recommends curl ca-certificates \
    && curl -LsSf https://astral.sh/uv/install.sh | sh \
    && apt-get clean && rm -rf /var/lib/apt/lists/*
    
ENV PATH="/root/.local/bin:$PATH"
ENV UV_PROJECT_ENVIRONMENT="/app/.venv"

WORKDIR /app

# Ensure /app/results directory exists
RUN mkdir -p /app/results

# Copy requirements/lockfile first (to leverage Docker layer caching)
COPY pyproject.toml uv.lock ./
# Install dependencies into /app/.venv
RUN uv sync --frozen --no-dev

# Copy application code
COPY src /app/src
COPY README.md /app/

# Install the project application code
RUN uv sync --frozen --no-dev

# Expose port
EXPOSE 8000

# Set Python path to include virtualenv
ENV PATH="/app/.venv/bin:$PATH"

# Startup command (runs FastAPI server which now includes APScheduler)
CMD ["uvicorn", "openrouter_free_model_scouter.main:app", "--host", "0.0.0.0", "--port", "8000"]
