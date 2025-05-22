import logging
import random
import time
from datetime import datetime
import os

def setup_logger():
    """Set up and return logger"""
    # Create logs directory if it doesn't exist
    os.makedirs("logs", exist_ok=True)
    
    # Configure logger
    logger = logging.getLogger("research_assistant")
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        
        # File handler
        file_handler = logging.FileHandler("logs/research_assistant.log")
        file_handler.setLevel(logging.INFO)
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        
        # Formatter
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        # Add handlers
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
    
    return logger

def get_random_delay(min_delay=2, max_delay=5):
    """Get random delay between min and max seconds"""
    return random.uniform(min_delay, max_delay)

def get_current_timestamp():
    """Get current timestamp in ISO format"""
    return datetime.now().isoformat()

def truncate_text(text, max_length=1000):
    """Truncate text to max_length"""
    if len(text) <= max_length:
        return text
    return text[:max_length] + "..."

def sanitize_filename(filename):
    """Sanitize filename to be safe for file systems"""
    # Replace invalid characters
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        filename = filename.replace(char, '_')
    return filename
