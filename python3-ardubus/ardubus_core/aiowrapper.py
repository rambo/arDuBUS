"""Helper class to allow using of command proxies etc in traditional blocking style
without having to deal with the ioloop"""
import asyncio
import functools
import inspect


class AIOWrapper:
    """Wraps all coroutine methods into asyncio run_until_complete calls"""
    _wrappedobj = None
    _loop = None

    def __init__(self, wrap_obj):
        self._wrappedobj = wrap_obj
        self._loop = asyncio.get_event_loop()
        for attr in functools.WRAPPER_ASSIGNMENTS:
            try:
                setattr(self, attr, getattr(self._wrappedobj, attr))
            except AttributeError:
                try:
                    setattr(self.__class__, attr, getattr(self._wrappedobj.__class__, attr))
                except AttributeError:
                    pass
                    # print("Could not copy {}".format(attr))

    def __getattr__(self, item):
        orig = getattr(self._wrappedobj, item)
        if inspect.iscoroutinefunction(orig):
            @functools.wraps(orig)
            def wrapped(*args, **kwargs):
                """Gets the waitable and tells the event loop to run it"""
                waitable = orig(*args, **kwargs)
                return self._loop.run_until_complete(waitable)
            return wrapped
        return orig

    def __dir__(self):
        return dir(self._wrappedobj)

    def quit(self):
        """Calls the device.quit via loop and closes the loop"""
        self._loop.run_until_complete(self._wrappedobj.quit())
        self._loop.close()
