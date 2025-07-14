#Each container uses a python 3.11-slim to fill the python 3.X requirement. 
#I selected slim to cut down on the overhead size of each container/microservice.
FROM python:3.11-slim

#establishes application root.
WORKDIR /app

# Install curl for health checks
RUN apt-get update && apt-get install -y curl sqlite3 && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY ground_station.py .
COPY templates/ templates/
COPY shared/ shared/

# Create shared directory for database with proper permissions
RUN mkdir -p /shared && chmod 777 /shared

# Expose port for web interface
EXPOSE 5000

# Environment variables
#Notably, there is no contact between the ground and the command-sender
#All actions are database-mediated to follow best microservice procedures
ENV PYTHONUNBUFFERED=1
ENV DATABASE_URL=sqlite:////shared/TECChallenge.db

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
  CMD curl -f http://localhost:5000/health || exit 1

# Run application
CMD ["python", "ground_station.py"]