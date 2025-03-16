import logging
import logging.config

LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": True,  # <-- ключевой момент
    "formatters": {
        "default": {
            "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "default",
            "level": "ERROR",  # Показываем только ERROR и выше
        },
    },
    "loggers": {
        "": {  # Корневой логгер
            "handlers": ["console"],
            "level": "ERROR",
        },
        # Логгеры socketio / engineio
        "socketio": {
            "handlers": ["console"],
            "level": "ERROR",
            "propagate": False
        },
        "socketio.server": {
            "handlers": ["console"],
            "level": "ERROR",
            "propagate": False
        },
        "engineio": {
            "handlers": ["console"],
            "level": "ERROR",
            "propagate": False
        },
        "engineio.server": {
            "handlers": ["console"],
            "level": "ERROR",
            "propagate": False
        },
        # Логгеры uvicorn
        "uvicorn": {
            "handlers": ["console"],
            "level": "ERROR",
            "propagate": False
        },
        "uvicorn.error": {
            "handlers": ["console"],
            "level": "ERROR",
            "propagate": False
        },
        "uvicorn.access": {
            "handlers": ["console"],
            "level": "ERROR",
            "propagate": False
        },
    },
}

def setup_logging():
    logging.config.dictConfig(LOGGING_CONFIG)
