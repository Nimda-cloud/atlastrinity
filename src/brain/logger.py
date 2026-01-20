import logging
from logging.handlers import RotatingFileHandler


def setup_logging(name: str = "brain"):
    """
    Setup logging configuration
    """
    from .config import LOG_DIR

    log_dir = LOG_DIR
    log_dir.mkdir(parents=True, exist_ok=True)

    log_file = log_dir / f"{name}.log"

    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    # Prevent propagation to root logger (avoid duplicate logs from uvicorn/other handlers)
    logger.propagate = False

    # Clear any existing handlers to prevent duplicates
    logger.handlers.clear()

    # File Handler (Rotating)
    # Max 10MB per file, keep 5 backups
    file_handler = RotatingFileHandler(
        log_file, maxBytes=10 * 1024 * 1024, backupCount=5, encoding="utf-8"
    )
    file_handler.setLevel(logging.INFO)
    file_formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)

    # Stream Handler (Console)
    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(logging.INFO)
    stream_formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    stream_handler.setFormatter(stream_formatter)
    logger.addHandler(stream_handler)

    return logger


# Create a default logger instance for convenient import
logger = setup_logging()
