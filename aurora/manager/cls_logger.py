"""LOGGER importer module for class use"""
import logging
import string

MAX_WIDTH = 0

class_loggers = []

class CustomFormatter(logging.Formatter):
    max_width = MAX_WIDTH
    def format(self, record):
        #print "class_loggers",class_loggers
        try:
            CustomFormatter.max_width = max(map(lambda mod_cls_name: len(mod_cls_name), class_loggers))
        except ValueError:
            pass
        mod_width = len(record.name)
        cls_width = 0

        try:
            (mod_name, cls_name) = record.name.rsplit('.', 1)
            mod_width = len(mod_name)
        except ValueError:
            (mod_name, cls_name) = (record.name, '')
        if self.max_width > 0 and self.max_width > mod_width:
            cls_width = self.max_width - mod_width
        # if mod_name == 'manager_http_server':
        #     print ("%s, %s, %s, %s, %s" % (mod_name, cls_name, mod_width, cls_width, self.max_width))

        return '[{0:-<{mod_width}}{1:->{cls_width}}]  {2}'.format(mod_name, cls_name, record.msg,
                                                                mod_width=mod_width, 
                                                                cls_width=cls_width)

def setup_handler():
    formatter = CustomFormatter()
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    return handler

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
    class_loggers.append(mod_cls_name)
    return cls.__class__.LOGGER