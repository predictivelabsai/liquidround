FROM python:3.13-slim

WORKDIR /app

# System deps for psycopg2, pdfplumber, etc.
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev && \
    rm -rf /var/lib/apt/lists/*

# Python deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# App code
COPY . .

# Create uploads dir
RUN mkdir -p /app/uploads

ENV PORT=5007
EXPOSE 5007

# Health check so Coolify's zero-downtime deploy flips the new container green
# quickly (start-period covers app boot + startup news fetch).
HEALTHCHECK --interval=15s --timeout=5s --start-period=45s --retries=5 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:5007/')" || exit 1

CMD ["python", "main.py"]
