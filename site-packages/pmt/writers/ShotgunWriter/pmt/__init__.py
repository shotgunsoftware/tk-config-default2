# ShotgunWriter. Copyright 2020 Imaginary Spaces. All Rights Reserved.

import logging
import os
from logging import config

from appdirs import user_data_dir

# configuring logger
log_file_folder = user_data_dir("pmt", "imgspc")
LOG_FILE_PATH = os.path.join(log_file_folder, "log.txt")

if not os.path.exists(log_file_folder):
    os.makedirs(log_file_folder)

# dict which configures the logging
logging_dict_config = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "precise": {
            "format": "%(asctime)s :: %(levelname)s :: %(funcName)s :: %(message)s"
        }
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "precise",
            "stream": "ext://sys.stdout",
        },
        "file": {
            "formatter": "precise",
            "class": "logging.handlers.RotatingFileHandler",
            "encoding": "utf-8",
            "filename": LOG_FILE_PATH,
        },
    },
    "loggers": {
        "": {"handlers": ["console", "file"], "level": "INFO"},
    },
}

logging.config.dictConfig(logging_dict_config)
logging.info("Logging configured to stdout and to file: " + LOG_FILE_PATH)
