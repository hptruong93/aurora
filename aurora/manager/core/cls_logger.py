"""LOGGER importer module for class use"""
import logging
import string

MAX_WIDTH = 0
MAX_WIDTH_LIMIT = 30

class_loggers = []

class CustomFormatter(logging.Formatter):
    """Extends logging.Formatter class with a custom formatting method"""
    
    max_width = MAX_WIDTH
    max_width_limit = MAX_WIDTH_LIMIT

    def normalize(self, width_map):
        """Normalizes a given mapping of module and class name lengths,
        zeroing values above self.max_width_limit.

        :param list width_map: List containing lengths of logger name strings
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
        """Formats the logged message to include a tag with the calling module
        and class name with the tag length no longer than specified 
        self.max_width_limit.
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
                width_map = map(lambda mod_cls_name: len(mod_cls_name), class_loggers)
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
        mod_width = len(mod_name)
        if self.max_width > 0 and self.max_width > mod_width:
            cls_width = self.max_width - mod_width

        return '[{0:-<{mod_width}}{1:->{cls_width}}]  {2}'.format(mod_name, 
                                                                  cls_name, 
                                                                  record.message,
                                                                  mod_width=mod_width, 
                                                                  cls_width=cls_width)

def setup_handler():
    """Sets up a StreamHandler on the root logger and assigns it a custom
    formatter.

    :rtype: logging.StreamHandler

    """
    formatter = CustomFormatter()
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    return handler

def set_up_root_logger(level=None):
    """Sets up the root logger with a handler created by setup_handler() method.
    Sets root logging level to provided level arg, defaults is WARN

    :param logging.level level: Desired level of logging, specified in logging module

    """
    stream_handler = setup_handler()
    logging.root.handlers.append(stream_handler)
    logging.root.setLevel(logging.INFO)

def get_cls_logger(cls):
    """Assign a logger to a class only if no prior logger has been assigned

    :param class cls: Class to which LOGGER should be assigned
    :rtype: logging.Logger

    """
    try:
        cls.__class__.LOGGER
    except AttributeError:
        cls.__class__.LOGGER = None
    mod_cls_name = '%s.%s' % (cls.__module__.replace('core.',''), cls.__class__.__name__)
    if cls.__class__.LOGGER is None:
        cls.__class__.LOGGER = logging.getLogger('%s.%s' % (cls.__module__, cls.__class__.__name__))
    elif cls.__class__.LOGGER.name != mod_cls_name:
        cls.__class__.LOGGER = logging.getLogger(mod_cls_name)
    class_loggers.append(mod_cls_name)
    return cls.__class__.LOGGER