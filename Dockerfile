FROM python:3.10-slim

WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Create a non-root user to run the app
RUN useradd -m appuser
USER appuser

# Default environment variable (can be overridden at runtime)
ENV PORT=8000
ENV TEST_MODE=false

# Expose the port for the API
EXPOSE 8000

# Use a proper entry point script
COPY docker-entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

ENTRYPOINT ["docker-entrypoint.sh"] 