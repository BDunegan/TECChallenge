# This Dockerfile works largely the same as in ground/Dockerfile but builds the command_sender instead

FROM python:3.11-slim

WORKDIR /app

# Install SQLite for database access
RUN apt-get update && apt-get install -y sqlite3 && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY command_sender.py .
COPY shared/ shared/

# Create shared directory for database access
RUN mkdir -p /shared && chmod 777 /shared

# Environment variables
ENV PYTHONUNBUFFERED=1
ENV DATABASE_URL=sqlite:////shared/TECChallenge.db
ENV SPACECRAFT_URL=http://spacecraft:8080/commands
ENV POLL_INTERVAL=5

# Run application
CMD ["python", "command_sender.py"]