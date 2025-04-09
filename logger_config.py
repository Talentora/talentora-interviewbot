import logging
import os
import sys
from datetime import datetime

def setup_logging(log_level=logging.DEBUG):
    """
    Set up enhanced logging with file and console handlers.
    
    Args:
        log_level: The logging level to use (default: DEBUG)
        
    Returns:
        The configured logger
    """
    # Create logs directory if it doesn't exist
    log_dir = "logs"
    os.makedirs(log_dir, exist_ok=True)
    
    # Configure logger with file and console handlers
    logger = logging.getLogger("voice-agent")
    logger.setLevel(log_level)
    
    # Clear any existing handlers (in case this is called multiple times)
    if logger.handlers:
        logger.handlers.clear()
    
    # Configure log format with timestamp, level, and module
    log_format = logging.Formatter('%(asctime)s - %(levelname)s - %(module)s - %(message)s')
    
    # Create file handler with date-based log file
    today = datetime.now().strftime("%Y-%m-%d")
    file_handler = logging.FileHandler(f"{log_dir}/voice-agent-{today}.log")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(log_format)
    
    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(log_format)
    
    # Add handlers to logger
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    # Log uncaught exceptions
    def handle_exception(exc_type, exc_value, exc_traceback):
        if issubclass(exc_type, KeyboardInterrupt):
            # Don't log keyboard interrupt
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return
            
        logger.critical("Uncaught exception", exc_info=(exc_type, exc_value, exc_traceback))
    
    # Set the exception hook
    sys.excepthook = handle_exception
    
    return logger

# Example usage:
# logger = setup_logging()
# logger.info("Application starting") 