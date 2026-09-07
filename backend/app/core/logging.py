"""Application logging setup."""

import logging
import logging.config


def configure_logging(log_level: str) -> None:
    """Configure concise console logging for the application."""

    logging.config.dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "default": {
                    "format": "%(asctime)s %(levelname)s "
                    "%(name)s: %(message)s",
                }
            },
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "formatter": "default",
                    "stream": "ext://sys.stderr",
                }
            },
            "root": {
                "level": log_level.upper(),
                "handlers": ["console"],
            },
        }
    )
