import logging
import logging.handlers
import os
import sys
from pathlib import Path


def console_log_handler():
    logStreamFormatter = logging.Formatter(
        fmt=f"%(levelname)-8s %(asctime)s \t %(filename)s @function %(funcName)s line %(lineno)s - %(message)s",
        datefmt="%H:%M:%S"
    )
    consoleHandler = logging.StreamHandler(stream=sys.stdout)
    consoleHandler.setFormatter(logStreamFormatter)
    consoleHandler.setLevel(level=logging.DEBUG)
    return consoleHandler


def file_log_handler(file_name):
    logFileFormatter = logging.Formatter(
        fmt=f"%(levelname)s %(asctime)s (%(relativeCreated)d) \t %(pathname)s F%(funcName)s L%(lineno)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Create a directory for logs if it doesn't exist
    log_directory = os.path.join(Path(os.getcwd()), 'app/logs')
    os.makedirs(log_directory, exist_ok=True)

    file_path = os.path.join(log_directory, file_name)

    # Create a TimedRotatingFileHandler
    fileHandler = logging.handlers.TimedRotatingFileHandler(
        filename=file_path,
        when="H",
        interval=1,
        backupCount=720,
        utc=True,
        delay=True
    )

    fileHandler.setFormatter(logFileFormatter)
    fileHandler.setLevel(level=logging.INFO)
    return fileHandler


class CustomExtraLogAdapter(logging.LoggerAdapter):
    def process(self, msg, kwargs):
        context = self.extra.get('extra') if self.extra else 'NO_CONTEXT'
        my_context = kwargs.pop('extra', context)
        return '[%s] %s' % (my_context, msg), kwargs


def get_logger(file_name="kyc_log.log"):
    """
        from app.logger import get_logger

        logger = get_logger()

        logger.info("Application started")
        logger.warning("This is a warning")
        logger.error("This is an error", extra={"extra": "OCRModule"})
    """
    # Use different logger names for standard and rejection logs
    logger_instance = logging.getLogger(file_name)
    logger_instance.setLevel(logging.DEBUG)

    # Ensure that the logger is initialized only once
    if not logger_instance.hasHandlers():
        # Prevent logger from propagating to higher level loggers
        logger_instance.propagate = False

        # Attach console handler
        console_handler = console_log_handler()
        logger_instance.addHandler(console_handler)

        # Determine the file name for the file handler
        file_handler = file_log_handler(file_name)
        logger_instance.addHandler(file_handler)
        logger_instance = CustomExtraLogAdapter(logger_instance, {"extra": None})

    return logger_instance
