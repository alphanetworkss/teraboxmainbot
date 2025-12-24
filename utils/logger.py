"""
Logging configuration using loguru.
Provides structured logging with rotation and different log levels.
"""
import sys
from pathlib import Path
from loguru import logger
from config.settings import settings


def setup_logger(service_name: str = "terabox_bot"):
    """
    Setup logger with file rotation and formatting.
    
    Args:
        service_name: Name of the service (main_bot or worker)
    """
    # Remove default handler
    logger.remove()
    
    # Console handler with colors
    logger.add(
        sys.stdout,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>",
        level=settings.log_level,
        colorize=True
    )
    
    # Create logs directory
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    # File handler with rotation
    logger.add(
        f"logs/{service_name}.log",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        level=settings.log_level,
        rotation=settings.log_file_max_size,
        retention="7 days",
        compression="zip",
        enqueue=True  # Thread-safe
    )
    
    # Error file handler
    logger.add(
        f"logs/{service_name}_errors.log",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        level="ERROR",
        rotation=settings.log_file_max_size,
        retention="30 days",
        compression="zip",
        enqueue=True
    )
    
    return logger


# Create default logger
log = setup_logger()
