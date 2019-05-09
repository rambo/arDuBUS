import logging


DEFAULT_LOG_FORMAT = '[%(asctime)s][%(levelname)s] %(name)s (%(process)d) %(pathname)s:%(funcName)s:%(lineno)d | %(message)s'


def init_logging():
    """Initialize logging, call this if you don't know any better logging arrangements"""
    logging.basicConfig(format=DEFAULT_LOG_FORMAT)
