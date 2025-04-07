# Stage 1: Build stage (if needed for compiled dependencies, not strictly necessary for this pure Python app)
# FROM python:3.10-slim as builder
# WORKDIR /build
# COPY requirements.txt .
# RUN pip wheel --no-cache-dir --wheel-dir /wheels -r requirements.txt

# Stage 2: Final stage
FROM python:3.10-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV APP_HOME /app

# Create app directory
WORKDIR $APP_HOME

# Install system dependencies if any were needed (e.g., for psycopg2 non-binary)
# RUN apt-get update && apt-get install -y --no-install-recommends libpq-dev gcc && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
# Copy only requirements first to leverage Docker cache
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt
    # If using a build stage:
    # COPY --from=builder /wheels /wheels
    # RUN pip install --no-cache-dir --no-index --find-links=/wheels -r requirements.txt && rm -rf /wheels

# Create a non-root user for security
RUN addgroup --system app && adduser --system --group app
# RUN useradd -m -u 1001 -s /bin/bash appuser

# Copy application code
# Copy the 'app' directory into the container
COPY ./app $APP_HOME/app

# Change ownership to the non-root user
# RUN chown -R app:app $APP_HOME
# USER app
# Note: Running as non-root might require adjusting permissions on volumes if used in production.
# For development with local volume mounts, running as root is often simpler.

# Expose the port the app runs on
EXPOSE 8000

# Define the command to run the application
# Use the command from docker-compose.yml for development (with --reload)
# For production, the command would be:
# CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
