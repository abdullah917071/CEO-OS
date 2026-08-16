FROM python:3.12-slim

ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# Install minimal system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md ./
COPY apps ./apps
COPY core ./core
COPY agents ./agents
COPY tools ./tools
COPY integrations ./integrations
COPY memory ./memory
COPY computer ./computer
COPY browser ./browser
COPY vision ./vision
COPY voice ./voice
COPY communications ./communications
COPY skills ./skills
COPY ceo_agent ./ceo_agent
COPY jarvis ./jarvis
COPY hermes ./hermes
COPY gstack ./gstack
COPY agency ./agency
COPY proactive ./proactive
COPY production ./production
COPY intelligence ./intelligence
COPY workflows ./workflows

RUN pip install --no-cache-dir . && python -m playwright install --with-deps chromium

EXPOSE 8000

CMD ["uvicorn", "apps.api.src.ceo_os_api.main:app", "--host", "0.0.0.0", "--port", "8000"]
