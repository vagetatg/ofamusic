FROM python:3.13-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    ffmpeg \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN pip install --no-cache-dir uv

# Copy dependency specifications first for better caching
COPY pyproject.toml .

# Install Python dependencies using uv
RUN uv pip install . --no-cache --system

# Copy application code
COPY . .

# Run the application
CMD ["uv", "run", "src"]
