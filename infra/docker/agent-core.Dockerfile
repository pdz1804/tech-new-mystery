FROM python:3.11-slim

WORKDIR /app

# System deps: curl for healthcheck, Playwright browser runtime
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    # Playwright Chromium runtime dependencies
    libnss3 libnspr4 libdbus-1-3 libatk1.0-0 libatk-bridge2.0-0 \
    libcups2 libxkbcommon0 libxcomposite1 libxdamage1 libxrandr2 \
    libgbm1 libpango-1.0-0 libcairo2 libasound2 libxshmfence1 \
    && rm -rf /var/lib/apt/lists/*

COPY agent_core/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright browser (Chromium only — used by browse_web tool)
RUN python -m playwright install chromium --with-deps

COPY agent_core ./agent_core

EXPOSE 8080

# BedrockAgentCoreApp exposes /ping (not /health)
HEALTHCHECK --interval=10s --timeout=5s --retries=5 \
    CMD curl -f http://localhost:8080/ping || exit 1

CMD ["python", "-m", "agent_core.server"]
