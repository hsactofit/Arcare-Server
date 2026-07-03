FROM python:3.12-slim

WORKDIR /app

# Install system dependencies needed for compiling python packages (like psycopg2)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose port 8000
EXPOSE 8000

# Make entrypoint script executable
RUN chmod +x entrypoint.sh

# Run entrypoint script
ENTRYPOINT ["./entrypoint.sh"]

