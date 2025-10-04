"""
Centralized logging configuration for Fast GraphRAG Document Analyzer
=====================================================================

Provides consistent logging across all modules with file rotation and
proper formatting.

Author: AI Assistant
Date: 2025-10-04
"""

import logging
import os
from logging.handlers import RotatingFileHandler
from datetime import datetime
from pathlib import Path


class AppLogger:
    """Centralized logger configuration with file rotation"""

    _loggers = {}
    _initialized = False

    @classmethod
    def setup_logging(cls, log_dir="./logs", log_level="INFO",
                     console_level=None, max_bytes=10*1024*1024, backup_count=30,
                     debug_mode=False):
        """
        Setup logging configuration with file rotation and flexible console output

        Args:
            log_dir: Directory for log files
            log_level: Logging level for file output (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            console_level: Logging level for console output (if None, uses log_level for debug_mode=True, WARNING otherwise)
            max_bytes: Maximum size of log file before rotation (default 10MB)
            backup_count: Number of backup files to keep (default 30)
            debug_mode: If True, shows all logs in console at log_level, otherwise only WARNING+
        """
        if cls._initialized:
            # Already initialized, just log a debug message
            logging.getLogger(__name__).debug("Logging already initialized, skipping setup")
            return

        # Create logs directory if it doesn't exist
        Path(log_dir).mkdir(parents=True, exist_ok=True)

        # Log file with timestamp
        log_filename = f"app_{datetime.now().strftime('%Y%m%d')}.log"
        log_filepath = os.path.join(log_dir, log_filename)

        # Determine console log level
        if console_level is None:
            console_level = log_level if debug_mode else "WARNING"
            
        # File log format (detailed)
        file_format = "[%(asctime)s] [%(levelname)s] [%(name)s:%(lineno)d] - %(message)s"
        file_date_format = "%Y-%m-%d %H:%M:%S"
        
        # Console log format (cleaner for debugging)
        console_format = "[%(levelname)s] %(name)s: %(message)s" if debug_mode else "[%(levelname)s] %(message)s"
        
        # Create formatters
        file_formatter = logging.Formatter(file_format, datefmt=file_date_format)
        console_formatter = logging.Formatter(console_format)

        # File handler with rotation
        file_handler = RotatingFileHandler(
            log_filepath,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding='utf-8'
        )
        file_handler.setFormatter(file_formatter)
        file_handler.setLevel(getattr(logging, log_level))

        # Console handler with flexible logging
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(console_formatter)
        console_handler.setLevel(getattr(logging, console_level))

        # Configure root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(getattr(logging, log_level))
        
        # Clear existing handlers to prevent duplicates
        root_logger.handlers.clear()
        
        root_logger.addHandler(file_handler)
        root_logger.addHandler(console_handler)

        cls._initialized = True

        # Log initialization
        root_logger.info("=" * 60)
        root_logger.info("Logging system initialized")
        root_logger.info(f"Log file: {log_filepath}")
        root_logger.info(f"File log level: {log_level}")
        root_logger.info(f"Console log level: {console_level}")
        root_logger.info(f"Debug mode: {debug_mode}")
        root_logger.info("=" * 60)

    @classmethod
    def reset_logging(cls):
        """Reset logging configuration - useful for testing or reconfiguration"""
        root_logger = logging.getLogger()
        root_logger.handlers.clear()
        cls._initialized = False
        cls._loggers.clear()

    @classmethod
    def get_logger(cls, name):
        """
        Get or create a logger for a specific module

        Args:
            name: Name of the logger (usually __name__)

        Returns:
            Logger instance
        """
        if name not in cls._loggers:
            cls._loggers[name] = logging.getLogger(name)
        return cls._loggers[name]


def get_logger(name):
    """
    Convenience function to get a logger

    Args:
        name: Name of the logger (usually __name__)

    Returns:
        Logger instance
    """
    return AppLogger.get_logger(name)


# Convenience functions for different logging modes
def init_logging(log_dir="./logs", log_level="INFO", console_level=None, debug_mode=False):
    """Initialize logging with custom configuration"""
    AppLogger.setup_logging(
        log_dir=log_dir, 
        log_level=log_level, 
        console_level=console_level,
        debug_mode=debug_mode
    )


def init_debug_logging(log_dir="./logs", log_level="DEBUG"):
    """Initialize logging in debug mode - shows all logs in console"""
    AppLogger.setup_logging(
        log_dir=log_dir, 
        log_level=log_level, 
        debug_mode=True
    )


def init_production_logging(log_dir="./logs", log_level="INFO"):
    """Initialize logging in production mode - only warnings/errors in console"""
    AppLogger.setup_logging(
        log_dir=log_dir, 
        log_level=log_level, 
        console_level="WARNING",
        debug_mode=False
    )


def init_silent_logging(log_dir="./logs", log_level="INFO"):
    """Initialize logging with no console output - file only"""
    AppLogger.setup_logging(
        log_dir=log_dir, 
        log_level=log_level, 
        console_level="CRITICAL",  # Effectively silent
        debug_mode=False
    )
