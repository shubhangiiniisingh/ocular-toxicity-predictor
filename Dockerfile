# Use official Python runtime as a parent image
FROM python:3.10-slim

# Install OS-level dependencies required by RDKit
RUN apt-get update && apt-get install -y \
    libxrender1 \
    libxext6 \
    libglib2.0-0 \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Set the working directory
WORKDIR /app

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Expose port and start FastAPI using Uvicorn
EXPOSE 8000
CMD uvicorn backend.app:app --host 0.0.0.0 --port $PORT
