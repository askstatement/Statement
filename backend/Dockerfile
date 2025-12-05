# Use an official slim Python base image
FROM python:3.10-slim

# Set environment variables to prevent .pyc creation and enable output flushing
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set working directory
WORKDIR /app

# Install system dependencies early for layer caching
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    tesseract-ocr \
    poppler-utils \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    && apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Pre-copy only requirements to leverage Docker cache
COPY requirements.txt .

# Upgrade pip and install Python dependencies
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# Copy the rest of the application code
COPY . .

# Expose port for Tornado
EXPOSE 8765

# Run the app using uvicorn
# uvicorn server:app --host 0.0.0.0 --port 8765 --workers 4 --loop uvloop --http httptools
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8765", "--workers", "4", "--loop", "uvloop", "--http", "httptools"]
