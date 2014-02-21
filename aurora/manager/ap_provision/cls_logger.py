"""LOGGER importer module for class use"""
import logging

def get_cls_logger(cls):
    """Assign a logger to a class only if no prior logger has been assigned

    :param class cls: Class to which LOGGER should be assigned

    """
    try:
        cls.__class__.LOGGER
    except AttributeError:
        cls.__class__.LOGGER = None
    mod_cls_name = '%s.%s' % (cls.__module__, cls.__class__.__name__)
    if cls.__class__.LOGGER is None:
        cls.__class__.LOGGER = logging.getLogger('%s.%s' % (cls.__module__, cls.__class__.__name__))
    elif cls.__class__.LOGGER.name != mod_cls_name:
        cls.__class__.LOGGER = logging.getLogger(mod_cls_name)
    return cls.__class__.LOGGER