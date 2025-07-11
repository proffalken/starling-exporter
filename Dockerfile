# Use official slim Python image
FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy exporter code
COPY exporter.py .

# Expose Prometheus metrics port
EXPOSE 8000

# Environment variable defaults (override at runtime)
ENV POLL_PERIOD_SECONDS=30 \
    EXPORTER_PORT=8000

# Run the exporter
CMD ["python", "exporter.py"]

