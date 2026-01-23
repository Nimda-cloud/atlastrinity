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

    # UI Log Handler (Streams to Redis for Electron)
    try:
        from .state_manager import state_manager

        class UIHandler(logging.Handler):
            def emit(self, record):
                try:
                    import asyncio
                    from datetime import datetime

                    # Format: HH:MM
                    log_time = datetime.fromtimestamp(record.created).strftime("%H:%M")
                    log_entry = {
                        "source": record.name,
                        "type": record.levelname.lower(),
                        "content": self.format(record),
                        "timestamp": log_time,
                    }

                    # Use fire-and-forget task if loop is running
                    try:
                        loop = asyncio.get_running_loop()
                        if loop.is_running():
                            loop.create_task(state_manager.publish_event("logs", log_entry))
                    except RuntimeError:
                        # Fallback for synchronous contexts - not ideal but prevents crash
                        pass
                except Exception:
                    pass

        ui_handler = UIHandler()
        ui_handler.setLevel(logging.INFO)
        # Cleaner formatter for UI: [SOURCE] MESSAGE
        ui_formatter = logging.Formatter("[%(name)s] %(message)s")
        ui_handler.setFormatter(ui_formatter)
        logger.addHandler(ui_handler)
    except Exception as e:
        print(f"Failed to setup UI Log Handler: {e}")

    return logger


# Create a default logger instance for convenient import
logger = setup_logging()
