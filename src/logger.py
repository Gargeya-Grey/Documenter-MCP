"""Logging configuration for the MCP Documentation Server."""

import sys
from pathlib import Path
from typing import Optional
from loguru import logger


def setup_logger(log_level: str = "INFO", log_file: Optional[str] = None) -> None:
    """Configure logging for the application."""
    
    # Remove default logger
    logger.remove()
    
    # Console logging with rich formatting
    logger.add(
        sys.stderr,
        level=log_level,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        colorize=True
    )
    
    # File logging if specified
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        logger.add(
            log_path,
            level=log_level,
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
            rotation="10 MB",
            retention="7 days",
            compression="zip"
        )
    
    logger.info(f"Logger initialized with level: {log_level}")


def get_logger(name: str):
    """Get a logger instance for a specific module."""
    return logger.bind(name=name)
