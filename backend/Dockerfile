# Base image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies (e.g. for psycopg2, if needed)
# python3-dev build-essential libpq-dev are often needed for psycopg2 compilation
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first to leverage Docker cache
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend code
COPY backend ./backend
COPY ml_training ./ml_training
# Also copy alembic config and migrations if they are in root or under backend
COPY alembic ./alembic
COPY alembic.ini .

# Copy data folder structure (dvc files) if needed, though dvc pull might be needed for real data
# For now, ensure data directory exists
RUN mkdir -p data

# Expose port
EXPOSE 8000

# Run the application
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
