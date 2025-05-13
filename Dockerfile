FROM python:3.10-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Download necessary files
RUN python session.py download-files

# Set environment variables (these will be overridden at runtime)
ENV LIVEKIT_URL=""
ENV LIVEKIT_API_KEY=""
ENV LIVEKIT_API_SECRET=""
ENV OPENAI_API_KEY=""
ENV CARTESIA_API_KEY=""
ENV DEEPGRAM_API_KEY=""

# Run the application
CMD ["python", "session.py", "dev"] 