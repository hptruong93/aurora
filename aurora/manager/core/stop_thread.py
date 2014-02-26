"""Module containing threads which can run a continuous
loop until a stop event is thrown.  Thread target code must
have a keyword argument for stop_event and must check
it periodically eg. 
    if stop_event.is_set(): break

"""
class StoppableThread(threading.Thread):
    """Thread class with a stop method to terminate timers
    that have been started"""
    def __init__(self, *args, **kwargs):
        kwargs = self.add_stop_argument(kwargs)
        super(StoppableThread, self).__init__(*args, **kwargs)

        self.LOGGER = get_cls_logger(self)
        self.LOGGER.debug("__init__ parent thread")
        self.LOGGER.debug(self)

    def add_stop_argument(self, kwargs):
        if 'kwargs' not in kwargs.keys():
            kwargs['kwargs'] = {}
        self._stop = threading.Event()
        kwargs['kwargs']['stop_event'] = self._stop
        return kwargs

    def stop(self):
        self._stop.set()
        #self.join()

    def stopped():
        return self._stop.is_set()

class TimerThread(StoppableThread):
    pass