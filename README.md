# AI Interview Bot

A FastAPI-based service that conducts automated AI interviews using Daily.co video calls, Cartesia TTS, and Claude AI.

## Features
- 🤖 AI-powered interview sessions
- 🎥 Automated video room creation
- 🗣️ Natural voice synthesis
- 🎙️ Voice activity detection
- 🔄 Real-time conversation processing

## Prerequisites
- Python 3.11+ (3.12 recommended)
- ffmpeg (required for audio processing)

## Quick Start

### 1. Environment Setup
```bash
# Clone repository
git clone <repository-url>
cd ai-interview-bot

# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
.\venv\Scripts\activate
# On Unix/MacOS:
source venv/bin/activate

# Upgrade pip and install build tools
python -m pip install --upgrade pip wheel setuptools

# Clean existing installations (if needed)
pip uninstall -y pydantic pydantic-core langchain-core pipecat-ai

# Install dependencies
pip install -r requirements.txt
```

### 2. Configuration
Create `.env` file in project root:
```env
DAILY_API_KEY=your_daily_key
CARTESIA_API_KEY=your_cartesia_key
ANTHROPIC_API_KEY=your_anthropic_key
DEEPGRAM_API_KEY=your_deepgram_key
AWS_ACCESS_KEY_ID=your_aws_access_key
AWS_SECRET_KEY=your_aws_secret_key
KOALA_FILTER_KEY=your_koala_key
```

### 3. Run the Application

#### Local Development
```bash
uvicorn app.main:app --reload --port 8000
```

#### Production Deployment
```bash
docker build -t interview-bot .
docker run -p 8000:8000 --env-file .env interview-bot
```

## API Usage

### Create Interview Session
```bash
curl -X POST http://localhost:8000/api/rooms/ \
  -H "Content-Type: application/json" \
  -d '{
    "voice_id": "your-voice-id",
    "interview_config": {
      "bot_name": "Sarah",
      "company_name": "TechCorp",
      "job_title": "Senior Engineer",
      "job_description": "Role description...",
      "company_context": "Company info...",
      "interview_questions": [
        "Tell me about your experience...",
        "How do you handle challenges?"
      ]
    }
  }'
```

### Response
```json
{
  "room_url": "https://domain.daily.co/room-name",
  "token": "room-token"
}
```

## Troubleshooting

### Common Issues

1. Dependency Conflicts
```bash
# If you encounter dependency conflicts:
pip uninstall -y pydantic pydantic-core langchain-core pipecat-ai
pip install -r requirements.txt --no-deps
pip install -r requirements.txt
```

2. FFmpeg Missing
```bash
# On Ubuntu/Debian:
sudo apt-get install ffmpeg

# On MacOS:
brew install ffmpeg

# On Windows:
choco install ffmpeg
```

3. Audio Processing Issues
- Ensure your system's audio devices are properly configured
- Check ffmpeg installation with `ffmpeg -version`
- Make sure all audio dependencies are installed:
  ```bash
  pip install Pillow==10.4.0 protobuf==4.25.5 pyloudnorm==0.1.1 scipy==1.14.1
  ```

## Development

### Project Structure
```
interview-bot/
├── app/
│   ├── api/         # API routes and models
│   ├── bot/         # Interview bot implementation
│   ├── services/    # External service integrations
│   └── core/        # Core configurations
├── Dockerfile
└── requirements.txt
```

## License
MIT