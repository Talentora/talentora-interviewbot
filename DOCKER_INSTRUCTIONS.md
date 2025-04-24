# Running the Voice Agent with Docker

## Prerequisites
- Docker and Docker Compose installed
- A `.env.local` file with the required environment variables:
  - `LIVEKIT_URL`
  - `LIVEKIT_API_KEY`
  - `LIVEKIT_API_SECRET`
  - `OPENAI_API_KEY`
  - `CARTESIA_API_KEY`
  - `DEEPGRAM_API_KEY`

## Running with Docker Compose (Recommended)

1. Build and start the container:
   ```bash
   docker-compose up -d
   ```

2. View logs:
   ```bash
   docker-compose logs -f
   ```

3. Stop the container:
   ```bash
   docker-compose down
   ```

## Running with Docker directly

1. Build the Docker image:
   ```bash
   docker build -t voice-agent .
   ```

2. Run the container:
   ```bash
   docker run -p 8080:8080 --env-file .env.local voice-agent
   ```

## Environment Variables

You can set up the environment variables by copying `.env.example` to `.env.local` and filling in the required values.
Alternatively, you can use the LiveKit CLI as mentioned in the README:

```bash
lk app env
``` 