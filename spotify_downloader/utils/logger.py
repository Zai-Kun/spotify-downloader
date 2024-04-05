import logging


class CustomFormatter(logging.Formatter):
    blue = "\x1b[1;34;40m"
    purple = "\x1b[1;35;40m"
    light_blue = "\x1b[1;32;40m"
    yellow = "\x1b[1;33;40m"
    red = "\x1b[31;1m"
    reset = "\x1b[0m"

    date_format = "%Y-%m-%d %H:%M:%S"

    _format = f"{purple}[%(asctime)s %(filename)s]{{color}} [%(levelname)s]:{reset} %(message)s"

    FORMATS = {
        logging.DEBUG: _format.format(color=blue),
        logging.INFO: _format.format(color=light_blue),
        logging.WARNING: _format.format(color=yellow),
        logging.ERROR: _format.format(color=red),
        logging.CRITICAL: _format.format(color=red),
    }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt, datefmt=self.date_format)
        return formatter.format(record)


def get_logger(level=None, formatter=None, name="root"):
    logger = logging.getLogger(name)
    stream_handler = logging.StreamHandler()

    if level:
        logger.setLevel(level)
    else:
        logger.setLevel(logging.INFO)

    if formatter:
        stream_handler.setFormatter(formatter)
    else:
        stream_handler.setFormatter(CustomFormatter())

    file_handler = logging.FileHandler(
        filename=f"{name}.log", encoding="utf-8", mode="w"
    )
    file_handler_formatter = logging.Formatter(
        "[{asctime}] [{levelname}] {name}: {message}", "%Y-%m-%d %H:%M:%S", style="{"
    )
    file_handler.setFormatter(file_handler_formatter)

    logger.addHandler(file_handler)
    logger.addHandler(stream_handler)

    return logger
