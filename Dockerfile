FROM python:3.12-slim

# Install system dependencies including FFmpeg for video/audio processing
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install Node.js 20 & pnpm for frontend build
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && npm install -g pnpm

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source
COPY . .

# Build React frontend bundle into frontend/dist
RUN pnpm --dir frontend install && pnpm --dir frontend run build

# Default port: Hugging Face Spaces uses 7860
EXPOSE 7860

ENV PORT=7860
ENV API_HOST=0.0.0.0

CMD ["python", "src/server.py"]
