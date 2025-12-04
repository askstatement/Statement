import os
import sys
import logging

LOG_FORMAT = "%(asctime)s [%(levelname)s] [%(name)s] - %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

def setup_logging():
    """Configure root loggers (app + uvicorn + fastapi)"""
    log_level = os.getenv("LOG_LEVEL", "info").lower()
    
    # Validate and set log level
    if log_level not in ["debug", "info", "warning", "error", "critical"]:
        print(f"[Logger] Invalid LOG_LEVEL '{log_level}', defaulting to INFO")
        log_level = "info"
    
    level = getattr(logging, log_level.upper())

    # Define formatter
    formatter = ColorFormatter(fmt=LOG_FORMAT, datefmt=DATE_FORMAT)

    # Create handler for console output
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(level)

    # Root logger (affects everything)
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    root_logger.handlers = [console_handler]

    # Uvicorn loggers
    for logger_name in ("uvicorn", "uvicorn.error", "uvicorn.access", "fastapi"):
        uvicorn_logger = logging.getLogger(logger_name)
        uvicorn_logger.setLevel(level)
        uvicorn_logger.handlers = [console_handler]
        uvicorn_logger.propagate = False

    print(f"[Logger] Initialized ({log_level.upper()} mode, level={logging.getLevelName(level)})")

class Logger:
    def __init__(self, name: str = "app"):
        self.logger = logging.getLogger(name)

    def debug(self, msg, *args, **kwargs):
        self.logger.debug(msg, *args, **kwargs)

    def info(self, msg, *args, **kwargs):
        self.logger.info(msg, *args, **kwargs)

    def warning(self, msg, *args, **kwargs):
        self.logger.warning(msg, *args, **kwargs)

    def error(self, msg, *args, **kwargs):
        self.logger.error(msg, *args, **kwargs)

    def exception(self, msg, *args, **kwargs):
        self.logger.exception(msg, *args, **kwargs)
        
class ColorFormatter(logging.Formatter):
    COLORS = {
        "DEBUG": "\033[36m",   # Cyan
        "INFO": "\033[32m",    # Green
        "WARNING": "\033[33m", # Yellow
        "ERROR": "\033[31m",   # Red
        "CRITICAL": "\033[1;31m", # Bold Red
    }
    RESET = "\033[0m"

    def format(self, record):
        color = self.COLORS.get(record.levelname, self.RESET)
        message = super().format(record)
        return f"{color}{message}{self.RESET}"
