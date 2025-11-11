import logging
import os
from logging.handlers import RotatingFileHandler


def setup_api_logger(log_path: str | None = None) -> logging.Logger:
    """Setup and return an application-wide logger for API errors.

    Creates a rotating file handler at `log_path` (defaults to ./logs/api.log).
    """
    if log_path is None:
        base = os.path.abspath(os.path.dirname(__file__))
        logs_dir = os.path.join(base, '..', 'logs')
        os.makedirs(logs_dir, exist_ok=True)
        log_path = os.path.join(logs_dir, 'api.log')

    logger = logging.getLogger('planificate.api')
    logger.setLevel(logging.INFO)

    # avoid adding multiple handlers if called multiple times
    if not logger.handlers:
        handler = RotatingFileHandler(log_path, maxBytes=5 * 1024 * 1024, backupCount=5, encoding='utf-8')
        formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(name)s: %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger
