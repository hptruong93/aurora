# 2014
# SAVI McGill: Heming Wen, Prabhat Tiwary, Kevin Han, Michael Smith &
#              Mike Kobierski 
#
"""Module containing threads which can run a continuous
loop until a stop event is thrown.  Thread target code must
have a keyword argument for ``stop_event`` and must check
it periodically eg.::

    import time
    from aurora.stop_thread import *

    def my_target(my_arg, stop_event=None):
        i = 0
        print "Your arg: %s" % my_arg
        while True:
            if stop_event.is_set():
                break
            print "Iteration %s." % i 
            i += 1
            time.sleep(1)

    t = StoppableThread(target=my_target, args=("This is some arg",))
    t.start()
    time.sleep(3.5)
    t.stop()
    t.join()

"""
import threading
import logging

from aurora.cls_logger import get_cls_logger

LOGGER = logging.getLogger(__name__)


class StoppableThread(threading.Thread):
    """Thread class with a stop method to any started threads 
    which have target callable executing a continuous loop.

    """
    def __init__(self, *args, **kwargs):
        """Sets up kwargs for stoppable thread."""
        kwargs = self.add_stop_argument(kwargs)
        super(StoppableThread, self).__init__(*args, **kwargs)

        self.LOGGER = get_cls_logger(self)
        self.LOGGER.debug("__init__ parent thread")
        self.LOGGER.debug(self)

    def add_stop_argument(self, kwargs):
        """Adds the ``'stop_event'`` argument to the keyword args 
        passed to the thread target.

        :param dict kwargs: Keyword arguments to pass to target 
        :returns: dict -- Keyword arguments including ``'stop_event'``

        """
        if 'kwargs' not in kwargs.keys():
            kwargs['kwargs'] = {}
        self._stop = threading.Event()
        kwargs['kwargs']['stop_event'] = self._stop
        return kwargs

    def stop(self):
        """Sets the stop event flag"""
        self._stop.set()
        #self.join()

    def stopped(self):
        """Check whether a thread has been stopped."""
        return self._stop.is_set()

class TimerThread(StoppableThread):
    """Same as :class:`StoppableThread`."""
    pass