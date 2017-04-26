import logging
from colorlog import ColoredFormatter
from logging.handlers import RotatingFileHandler

COLOR_FORMAT = "%(log_color)s[%(levelname)s]%(reset)s %(purple)s%(name)s %(processName)s %(reset)s %(bold_blue)s%(funcName)s%(reset)s %(green)s%(asctime)s%(reset)s \n%(message_log_color)s%(message)s"

FORMAT = "%(levelname)s %(name)s %(processName)s %(funcName)s %(asctime)s\n%(message)s"

DATEFMT = '%Y/%m/%d %H:%M:%S'

def get_logger(name, level=logging.DEBUG):
    _formatter = ColoredFormatter(
        COLOR_FORMAT,
        datefmt=DATEFMT,
        reset=True,
        log_colors={
            'DEBUG': 'cyan',
            'INFO': 'green',
            'WARNING': 'yellow',
            'ERROR': 'red',
            'CRITICAL': 'red',
        },
        secondary_log_colors={
            'message': {
                'DEBUG': 'cyan',
                'INFO': 'green',
                'WARNING': 'bold_yellow',
                'ERROR': 'bold_red',
                'CRITICAL': 'bold_red'
            }
        }
    )
    _handler = logging.StreamHandler()
    _handler.setFormatter(_formatter)

    handler = RotatingFileHandler("dandelion.log",
                                   maxBytes=1024*1024,
                                   backupCount=1)
    log_formatter = logging.Formatter(FORMAT, DATEFMT)
    handler.setFormatter(log_formatter)

    logger = logging.getLogger(name)
    logger.addHandler(_handler)
    logger.addHandler(handler)
    logger.setLevel(level=level)
    return logger

