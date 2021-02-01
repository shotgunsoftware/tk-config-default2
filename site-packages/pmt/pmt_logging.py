# ImgSpc-PMT. Copyright 2020 Imaginary Spaces. All Rights Reserved.
import os
from appdirs import user_data_dir

# logging dict config
log_file_folder = user_data_dir("pmt", "imgspc")
LOG_FILE_PATH = os.path.join(log_file_folder, "log.txt")
_logging_dict_config = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "precise": {
            "format": "%(asctime)s:%(levelname)s:%(name)s:%(funcName)s:%(message)s"
        }
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "precise",
            "stream": "ext://sys.stdout",
            "level": "INFO",
        },
        "file": {
            "formatter": "precise",
            "class": "logging.handlers.RotatingFileHandler",
            "encoding": "utf-8",
            "filename": LOG_FILE_PATH,
            "level": "DEBUG",
        },
    },
    "loggers": {
        "": {"handlers": ["console", "file"], "level": "DEBUG"},
    },
}

_initialized = False


def initialize():
    import logging
    import logging.config

    global _initialized
    if _initialized:
        return

    # configuring logger
    if not os.path.exists(log_file_folder):
        os.makedirs(log_file_folder)

    logging.config.dictConfig(_logging_dict_config)
    logging.info("Logging configured to stdout and to file: " + LOG_FILE_PATH)

    _initialized = True
