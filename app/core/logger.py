from loguru import logger
import sys

# Remove default logger
logger.remove()

# Add file logger for interview_bot.log
logger.add(
    "./logs/interview_bot.log",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
    level="DEBUG",
    rotation="1 day",
    retention="7 days" 
)


# Add custom logging configuration
logger.add(
    sys.stderr,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}:{function}:{line}</cyan> - <white>{message}</white>",
    level="INFO",
    colorize=True
)


logger.add(
    sys.stderr,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}:{function}:{line}</cyan> - <yellow>{message}</yellow>",
    level="WARNING",
    colorize=True
)

logger.add(
    sys.stderr,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}:{function}:{line}</cyan> - <red>{message}</red>",
    level="CRITICAL",
    colorize=True
) 

# logger.add(
#     sys.stderr,
#     format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}:{function}:{line}</cyan> - <blue>{message}</blue>",
#     level="DEBUG",
#     colorize=True
# )