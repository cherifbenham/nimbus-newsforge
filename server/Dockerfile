FROM python:3.12-slim-bookworm

# Work inside /app
WORKDIR /app

# Install minimal build deps for common Python wheels (grpcio etc.)
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*

# Preinstall requirements
COPY requirements.txt .
RUN pip install --upgrade pip setuptools \
    && pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

EXPOSE 5001
CMD ["python", "app.py"]
