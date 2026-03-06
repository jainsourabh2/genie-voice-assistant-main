# Dual logging: file-based and terminal with colors
# Supports automatic log rotation by size (10MB max, 5 backup files)
import logging
import os
from datetime import datetime
from logging.handlers import RotatingFileHandler
from colorama import Fore, Style, init

from config import LOG_DIR, LOG_LEVEL

# Log rotation settings
MAX_LOG_SIZE = 10 * 1024 * 1024  # 10 MB per log file
BACKUP_COUNT = 5  # Keep 5 backup files (e.g., app.log.1, app.log.2, etc.)

# Initialize colorama
init(autoreset=True)

class ColoredFormatter(logging.Formatter):
    """Custom formatter with color coding for terminal output"""

    COLORS = {
        'DEBUG': Fore.CYAN,
        'INFO': Fore.GREEN,
        'WARNING': Fore.YELLOW,
        'ERROR': Fore.RED,
        'CRITICAL': Fore.RED + Style.BRIGHT,
    }

    def format(self, record):
        color = self.COLORS.get(record.levelname, '')
        record.levelname = f"{color}{record.levelname}{Style.RESET_ALL}"
        record.msg = f"{color}{record.msg}{Style.RESET_ALL}"
        return super().format(record)


class FileFormatter(logging.Formatter):
    """Plain formatter for file output"""
    pass


def setup_logger(name: str) -> logging.Logger:
    """Set up a logger with both file and terminal handlers"""
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, LOG_LEVEL.upper()))

    # Avoid adding handlers multiple times
    if logger.handlers:
        return logger

    # Create log directory if it doesn't exist
    os.makedirs(LOG_DIR, exist_ok=True)

    # File handler - daily log files with automatic rotation
    # Rotates when file exceeds MAX_LOG_SIZE, keeps BACKUP_COUNT old files
    log_filename = os.path.join(LOG_DIR, f"{datetime.now().strftime('%Y-%m-%d')}.log")
    file_handler = RotatingFileHandler(
        log_filename,
        maxBytes=MAX_LOG_SIZE,
        backupCount=BACKUP_COUNT
    )
    file_handler.setLevel(logging.DEBUG)
    file_formatter = FileFormatter(
        '%(asctime)s | %(name)s | %(levelname)s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(file_formatter)

    # Terminal handler with colors
    console_handler = logging.StreamHandler()
    console_handler.setLevel(getattr(logging, LOG_LEVEL.upper()))
    console_formatter = ColoredFormatter(
        '%(asctime)s | %(name)s | %(levelname)s | %(message)s',
        datefmt='%H:%M:%S'
    )
    console_handler.setFormatter(console_formatter)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger


# Pre-configured loggers
def get_logger(name: str = "chatbot") -> logging.Logger:
    """Get or create a logger with the given name"""
    return setup_logger(name)
