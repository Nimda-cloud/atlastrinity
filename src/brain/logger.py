import logging
import re
import sys
from logging.handlers import RotatingFileHandler


class SecretFilter(logging.Filter):
    """Filter that masks sensitive information in logs."""

    def __init__(self, name: str = ""):
        super().__init__(name)
        # Patterns to mask: ghu_..., ghp_..., mistral keys, etc.
        self.patterns = [
            re.compile(r"gh[up]_[a-zA-Z0-9]{30,60}"),  # GitHub tokens
            re.compile(r"AIzaSy[a-zA-Z0-9_-]{33}"),  # Google API Keys
            re.compile(r"Bearer\s+[a-zA-Z0-9._-]+"),  # Bearer tokens
        ]

    def filter(self, record):
        if not isinstance(record.msg, str):
            return True

        for pattern in self.patterns:
            record.msg = pattern.sub("[MASKED]", record.msg)

        # Also check arguments if they are strings
        if record.args:
            new_args = []
            for arg in record.args:
                if isinstance(arg, str):
                    for pattern in self.patterns:
                        arg = pattern.sub("[MASKED]", arg)
                new_args.append(arg)
            record.args = tuple(new_args)

        return True


def setup_logging(name: str = "brain"):
    """Setup logging configuration"""
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
        log_file,
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setLevel(logging.INFO)
    file_formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    file_handler.setFormatter(file_formatter)
    file_handler.addFilter(SecretFilter())
    logger.addHandler(file_handler)

    # Stream Handler (Console)
    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(logging.INFO)
    stream_formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    stream_handler.setFormatter(stream_formatter)
    stream_handler.addFilter(SecretFilter())
    logger.addHandler(stream_handler)

    # UI Log Handler (Streams to Redis for Electron)
    try:

        class UIHandler(logging.Handler):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self._is_emitting = False

            def emit(self, record):
                if self._is_emitting:
                    return

                try:
                    self._is_emitting = True
                    import asyncio
                    from datetime import datetime

                    # Local import to avoid circular dependency with setup_logging
                    from .state_manager import state_manager

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
                        # Try to get the current loop, if it exists and is running
                        loop = None
                        try:
                            loop = asyncio.get_running_loop()
                        except RuntimeError:
                            # No running loop in this thread
                            pass

                        if loop and loop.is_running() and not loop.is_closed():
                            loop.create_task(state_manager.publish_event("logs", log_entry))
                    except (RuntimeError, AttributeError):
                        # Fallback for synchronous contexts or closed loop
                        pass
                except Exception:
                    pass
                finally:
                    self._is_emitting = False

        ui_handler = UIHandler()
        ui_handler.setLevel(logging.INFO)
        # Cleaner formatter for UI: [SOURCE] MESSAGE
        ui_formatter = logging.Formatter("[%(name)s] %(message)s")
        ui_handler.setFormatter(ui_formatter)
        ui_handler.addFilter(SecretFilter())
        logger.addHandler(ui_handler)
    except Exception as e:
        print(f"Failed to setup UI Log Handler: {e}", file=sys.stderr)

    return logger


# Create a default logger instance for convenient import
logger = setup_logging()
