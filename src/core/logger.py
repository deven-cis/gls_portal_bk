import os
import logging
from datetime import datetime
from colorlog import ColoredFormatter

LOG_LEVEL = logging.INFO
LOG_DIR = 'log_files'
os.makedirs(LOG_DIR, exist_ok=True)

# Define formatters
COLOR_LOG_FORMAT = "%(log_color)s%(asctime)s - %(filename)s - %(levelname)s - %(message)s"
PLAIN_LOG_FORMAT = "%(asctime)s - %(filename)s - %(levelname)s - %(message)s"

color_formatter = ColoredFormatter(
    COLOR_LOG_FORMAT,
    datefmt="%Y-%m-%d %H:%M:%S",
    reset=True,
    log_colors={
        'DEBUG': 'cyan',
        'INFO': 'blue',
        'WARNING': 'yellow',
        'ERROR': 'red',
        'CRITICAL': 'bold_red',
    }
)

file_formatter = logging.Formatter(
    PLAIN_LOG_FORMAT,
    datefmt="%Y-%m-%d %H:%M:%S"
)

# Setup logger
logger = logging.getLogger(__name__)
logger.setLevel(LOG_LEVEL)

# ✅ Avoid adding duplicate handlers
if not logger.handlers:
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(color_formatter)
    logger.addHandler(console_handler)

    # File handler
    log_file_name = f"app_{datetime.now().strftime('%Y-%m-%d')}.log"
    log_file_path = os.path.join(LOG_DIR, log_file_name)
    file_handler = logging.FileHandler(log_file_path, mode='a')
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)

logger.propagate = False