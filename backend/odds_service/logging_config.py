"""
Logging Configuration Module for WindFall ML API.

This module sets up centralized logging configuration for the entire API.
It configures log levels, formats, and handlers to ensure consistent
logging across all modules.
"""

import logging
import sys


def setup_logging():
    """
    Configures centralized logging for the ML API.
    
    Sets up logging with INFO level by default, formats log messages
    with timestamps and module names, and outputs to stdout. Also
    reduces verbosity of third-party loggers (uvicorn, mysql.connector)
    to WARNING level to reduce noise in logs.
    
    This function should be called once at application startup.
    """
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - [%(levelname)s] - %(name)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    # Silence overly verbose loggers from third-party libraries
    # uvicorn.access logs every HTTP request which is too noisy
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    # mysql.connector can be verbose about connection details
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)

    logging.info("Logging configured.")