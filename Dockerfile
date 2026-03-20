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

CMD ["python", "main.py"]
