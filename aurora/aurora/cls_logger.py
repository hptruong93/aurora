# 2014
# SAVI McGill: Heming Wen, Prabhat Tiwary, Kevin Han, Michael Smith,
#              Mike Kobierski and Hoai Phuoc Truong
#
"""LOGGER importer module for class use."""

import logging
import string

LOGGER = logging.getLogger(__name__)
MAX_WIDTH = 0
MAX_WIDTH_LIMIT = 30

class_loggers = []

class CustomFormatter(logging.Formatter):
    """Extends logging.Formatter class with a custom formatting method.

    Usage::

        import logging
        from aurora import cls_logger
        class A():
            def __init__(self):
                self.LOGGER = cls_logger.get_cls_logger(self)

            def hello_world(self):
                # String substitutions work
                self.LOGGER.info("%s World!", "Hello")

        def main():
            cls_logger.set_up_root_logger(level=logging.INFO)
            a = A()
            a.hello_world()
            a.LOGGER.warn("This works too.")

    """

    max_width = MAX_WIDTH
    max_width_limit = MAX_WIDTH_LIMIT

    def normalize(self, width_map):
        """Normalizes a given mapping of module and class name lengths,
        zeroing values above ``self.max_width_limit``.

        :param list width_map: List containing lengths of logger 
                               name mistrings
        :rtype: list

        """
        return_map = []
        for width in width_map:
            if width > self.max_width_limit:
                return_map.append(0)
            else:
                return_map.append(width)
        return return_map

    def format(self, record):
        """Formats the logged message to include a tag with the 
        calling module and class name with the tag length no longer 
        than specified ``self.max_width_limit``.  Also tracks which 
        classes are calling the format function, if it is a new 
        class the class name is added to ``class_loggers`` list.::

            [module_name----ClassName] Logged Message

        :param LogRecord record: LogRecord with log information
        :rtype: str

        """
        record.name = record.name.replace('core.', '')
        if record.name not in class_loggers:
            class_loggers.append(record.name)
        #print "record.name:",record.name
        #print "class_loggers", class_loggers
        record.message = record.getMessage()
        (mod_width, cls_width) = (len(record.name), 0)
        (mod_name, cls_name) = (None, None)
        max_width = 0
        if self.max_width == 0:
            max_width = mod_width
        else:
            try:
                width_map = map(lambda mod_cls_name: len(mod_cls_name),
                                class_loggers)
            except ValueError:
                pass
            else:
                width_map = self.normalize(width_map)
                max_width = max(width_map)
        CustomFormatter.max_width = max_width + 1
        try:
            (mod_name, cls_name) = record.name.rsplit('.', 1)
        except ValueError:
            (mod_name, cls_name) = (record.name, '')
        mod_width = len(mod_name) + 1
        if self.max_width > 0 and self.max_width > mod_width:
            cls_width = self.max_width - mod_width

        return '[{0:-<{mod_width}}{1:->{cls_width}}]  {2}'.format(
            mod_name, 
            cls_name, 
            record.message,
            mod_width=mod_width, 
            cls_width=cls_width
        )

def setup_handler():
    """Sets up a StreamHandler on the root logger and assigns it a 
    custom formatter.

    :rtype: :class:`logging.StreamHandler`

    """
    formatter = CustomFormatter()
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    return handler

def set_up_root_logger(level=None):
    """Sets up the root logger with a handler created by 
    setup_handler() method. Sets root logging level to provided 
    level arg, defaults is WARN

    :param level: Desired level of logging, specified in logging module
    :type level: int -- `logging.level \
       <https://docs.python.org/2/library/logging.html#logging-levels>`_
    """
    stream_handler = setup_handler()
    logging.root.handlers.append(stream_handler)
    logging.root.setLevel(logging.INFO)
    if level is not None:
        LOGGER.debug("Setting logging level to %s", level)
        logging.root.setLevel(level)

def get_cls_logger(cls):
    """Assign a logger to a class only if no prior logger has 
    been assigned

    :param class cls: Class to which LOGGER should be assigned
    :rtype: :class:`logging.Logger`

    """
    try:
        cls.__class__.LOGGER
    except AttributeError:
        cls.__class__.LOGGER = None
    mod_cls_name = '%s.%s' % (
        cls.__module__.replace('core.',''), 
        cls.__class__.__name__
    )
    if cls.__class__.LOGGER is None:
        cls.__class__.LOGGER = logging.getLogger(
            '%s.%s' % (
                cls.__module__, 
                cls.__class__.__name__
            )
        )
    elif cls.__class__.LOGGER.name != mod_cls_name:
        cls.__class__.LOGGER = logging.getLogger(mod_cls_name)
    class_loggers.append(mod_cls_name)
    return cls.__class__.LOGGER