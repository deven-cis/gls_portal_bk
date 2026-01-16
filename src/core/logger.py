"""
Logger module with date-wise rotation and code tracking.
All logger functionality in one file for simplicity.
"""

import os
import logging
from datetime import datetime
from logging.handlers import RotatingFileHandler
from colorlog import ColoredFormatter

# Configuration
LOG_LEVEL = logging.INFO
LOG_DIR = 'log_files'
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
os.makedirs(LOG_DIR, exist_ok=True)

# Log format with code tracking
LOG_FORMAT = "%(asctime)s - %(filename)s:%(lineno)d - %(funcName)s() - %(levelname)s - %(message)s"


def get_log_filename():
    """Get log filename for today with rotation number if needed."""
    today = datetime.now().strftime('%Y-%m-%d')
    base_path = os.path.join(LOG_DIR, f"app_{today}.log")
    
    if not os.path.exists(base_path):
        return base_path
    
    try:
        if os.path.getsize(base_path) < MAX_FILE_SIZE:
            return base_path
    except OSError:
        return base_path
    
    for num in range(1, 1000):
        rotated_path = os.path.join(LOG_DIR, f"app_{today}_{num}.log")
        if not os.path.exists(rotated_path):
            return rotated_path
        try:
            if os.path.getsize(rotated_path) < MAX_FILE_SIZE:
                return rotated_path
        except OSError:
            return rotated_path
    
    return base_path


class DateRotatingHandler(RotatingFileHandler):
    """Rotates logs by date and size (10MB)."""
    
    def __init__(self):
        super().__init__(get_log_filename(), maxBytes=MAX_FILE_SIZE, backupCount=0, encoding='utf-8')
        self.current_date = datetime.now().strftime('%Y-%m-%d')
    
    def shouldRollover(self, record):
        """Rollover if date changed or file size exceeded."""
        today = datetime.now().strftime('%Y-%m-%d')
        if today != self.current_date:
            return True
        return super().shouldRollover(record)
    
    def doRollover(self):
        """Create new log file when rotating."""
        if self.stream:
            self.stream.close()
            self.stream = None
        self.baseFilename = get_log_filename()
        self.current_date = datetime.now().strftime('%Y-%m-%d')
        if not self.delay:
            self.stream = self._open()


# Setup logger
logger = logging.getLogger('gls_app')
logger.setLevel(LOG_LEVEL)

if not logger.handlers:
    # Console handler (colored)
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(ColoredFormatter(
        f"%(log_color)s{LOG_FORMAT}",
        datefmt="%Y-%m-%d %H:%M:%S",
        log_colors={
            'DEBUG': 'cyan',
            'INFO': 'blue',
            'WARNING': 'yellow',
            'ERROR': 'red',
            'CRITICAL': 'bold_red'
        }
    ))
    logger.addHandler(console_handler)
    
    # File handler (date-wise rotation, 10MB limit)
    try:
        file_handler = DateRotatingHandler()
        file_handler.setFormatter(logging.Formatter(LOG_FORMAT, datefmt="%Y-%m-%d %H:%M:%S"))
        logger.addHandler(file_handler)
    except Exception as e:
        logger.warning(f"File handler initialization failed: {e}")
    
    logger.propagate = False
