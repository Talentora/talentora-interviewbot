# Use the official Python image from the Docker Hub
FROM python:3.11-slim

ENV PYTHONWARNINGS="ignore"

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container
COPY requirements.txt .

# Install dependencies in a single layer
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    portaudio19-dev \
    libportaudio2 \
    libportaudiocpp0 \
    ffmpeg \
    && pip install --no-cache-dir --quiet -r requirements.txt \
    && apt-get purge -y --auto-remove build-essential \
    && rm -rf /var/lib/apt/lists/* \
    && rm -rf ~/.cache/pip

# Copy the entire application code into the container
COPY . .

# Expose the port the app runs on
EXPOSE 8000

# Command to run the FastAPI app using uvicorn
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]