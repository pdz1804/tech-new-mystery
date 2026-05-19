FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN pip install --no-cache-dir poetry==1.7.1

# Configure Poetry to not create virtualenv (install to system Python)
ENV POETRY_VIRTUALENVS_CREATE=false

# Copy only dependency files (for Docker layer caching)
COPY pyproject.toml poetry.lock* ./

# Install dependencies only (app package installed manually below)
RUN poetry install --no-root

# Copy application code
COPY . .

# Install app package
RUN pip install --no-cache-dir -e .

CMD ["poetry", "run", "celery", "-A", "app.workers.celery_app", "worker", "--loglevel=info"]
