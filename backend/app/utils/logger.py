"""
Logging configuration
"""
import structlog
import logging
import sys
from app.config import settings


def configure_logging():
    """
    Configure structured logging for the application
    """
    # Set log level based on environment
    log_level = logging.DEBUG if settings.environment == "development" else logging.INFO
    
    # Configure standard logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=log_level,
    )
    
    # Configure structlog
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.CallsiteParameterAdder(
                parameters=[
                    structlog.processors.CallsiteParameter.FILENAME,
                    structlog.processors.CallsiteParameter.LINENO,
                ]
            ),
            structlog.dev.ConsoleRenderer() if settings.environment == "development"
            else structlog.processors.JSONRenderer(),
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
    
    # Get logger instance
    logger = structlog.get_logger()
    logger.info(
        "Logging configured",
        environment=settings.environment,
        log_level=logging.getLevelName(log_level)
    )
    
    return logger