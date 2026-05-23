FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for Playwright browsers
RUN apt-get update && apt-get install -y \
    curl \
    wget \
    ca-certificates \
    fonts-liberation \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libatspi2.0-0 \
    libcups2 \
    libdbus-1-3 \
    libgbm1 \
    libgtk-3-0 \
    libnspr4 \
    libnss3 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libx11-6 \
    libxcb1 \
    libxcomposite1 \
    libxdamage1 \
    libxext6 \
    libxfixes3 \
    libxrandr2 \
    libxss1 \
    xdg-utils \
    && rm -rf /var/lib/apt/lists/*

# Copy only dependency files first for Docker layer caching
COPY requirements.txt ./

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright browsers (playwright is already in requirements.txt)
# Use --with-deps to install system dependencies that Playwright needs
RUN playwright install --with-deps chromium

# Copy application code
COPY . .

CMD ["celery", "-A", "app.workers.celery_app", "worker", "--loglevel=info"]
