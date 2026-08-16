FROM python:3.12-slim

ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

WORKDIR /app
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
RUN pip install --no-cache-dir . && python -m playwright install --with-deps chromium

CMD ["uvicorn", "apps.api.src.ceo_os_api.main:app", "--host", "0.0.0.0", "--port", "8000"]
