import os
import logging

def configure_logging(service_name):
    """
    Configure logging with support for environment variables to control log levels
    
    Args:
        service_name: Name of the service for the logger
        
    Returns:
        A configured logger instance
    """
    # Get log level from environment variable or default to INFO
    log_level_name = os.getenv("LOG_LEVEL", "INFO").upper()
    
    # Validate log level
    valid_levels = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
        "CRITICAL": logging.CRITICAL
    }
    
    log_level = valid_levels.get(log_level_name, logging.INFO)
    
    # Create handlers
    file_handler = logging.FileHandler(f"{service_name}.log")
    console_handler = logging.StreamHandler()
    
    # Configure basic logging
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[file_handler, console_handler]
    )
    
    # Get the logger for this service
    logger = logging.getLogger(service_name)
    
    # Configure werkzeug logger separately
    werkzeug_logger = logging.getLogger('werkzeug')
    # Warning level for file but still show INFO in console
    werkzeug_logger.setLevel(logging.WARNING)
    werkzeug_handler = logging.StreamHandler()
    werkzeug_handler.setLevel(logging.INFO)
    werkzeug_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    werkzeug_logger.addHandler(werkzeug_handler)
    
    # Only log Flask startup info if debug is enabled
    flask_logger = logging.getLogger('flask')
    flask_logger.setLevel(logging.WARNING)
    
    # Log the current configuration
    logger.debug(f"Logging configured for {service_name} at level {log_level_name}")
    
    return logger 