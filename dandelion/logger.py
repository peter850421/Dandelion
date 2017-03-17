import logging
from colorlog import ColoredFormatter


def get_logger(name, level=logging.DEBUG):
    _formatter = ColoredFormatter(
        "%(log_color)s[%(levelname)s]%(reset)s %(purple)s%(name)s %(processName)s %(reset)s %(bold_blue)s%("
        "funcName)s%(reset)s %(green)s%(asctime)s%(reset)s \n%(message_log_color)s%(message)s",
        datefmt='%Y/%m/%d %H:%M:%S',
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
    logger = logging.getLogger(name)
    logger.addHandler(_handler)
    logger.setLevel(level=level)
    return logger

