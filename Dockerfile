FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY backend/ ./backend/
COPY frontend/ ./frontend/

# Create output dirs and volumes
RUN mkdir -p generated_apps backend/evaluation/results
VOLUME ["/app/generated_apps", "/app/backend/evaluation/results"]

# Copy .env.example as default .env
COPY .env.example .env

# Expose port
EXPOSE 8000

# Healthcheck using python's built-in urllib
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# Run
CMD ["python", "-m", "uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
