# Voice Agent Logging System

This document describes the logging setup for the Voice Agent application.

## Logging Structure

The application uses Python's built-in `logging` module with a custom configuration to provide comprehensive logging capabilities. All logs are:

1. Written to date-stamped files in the `logs/` directory
2. Displayed in the console with different verbosity levels
3. Formatted with timestamps, log levels, and source module information

## Log Levels

The system uses the following log levels:

- **DEBUG**: Detailed information, typically of interest only when diagnosing problems (written to log files only)
- **INFO**: Confirmation that things are working as expected (displayed in console and log files)
- **WARNING**: Indication that something unexpected happened, but the application is still working
- **ERROR**: A more serious problem that prevented a specific function from working
- **CRITICAL**: A serious error that might prevent the program from continuing

## Key Log Points

The application logs events at these critical points:

1. **Application lifecycle**:
   - Application startup and shutdown
   - Room connection and status
   - Participant joining and details

2. **Voice agent operation**:
   - VAD (Voice Activity Detection) loading
   - Agent creation and configuration
   - System prompt construction
   - User speech transcription
   - Agent speaking events

3. **Context and metadata**:
   - Extraction of context from participant metadata
   - Building of system prompts from context
   - Generation of personalized greetings

4. **Error handling**:
   - All exceptions with traceback information
   - Service failures 
   - Communication errors

## Log File Location

Logs are stored in:
```
logs/voice-agent-YYYY-MM-DD.log
```

Where `YYYY-MM-DD` is the current date.

## Exception Handling

The logging system includes a global exception handler that ensures all uncaught exceptions are properly logged with full traceback information before the application terminates.

## Usage

The centralized logging configuration is in `logger_config.py`. To use the logger in any module:

```python
import logging
from logger_config import setup_logging

# For the first module that initializes logging:
logger = setup_logging()

# For all other modules:
logger = logging.getLogger("voice-agent")
``` 