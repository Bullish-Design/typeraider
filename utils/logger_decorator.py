import functools
import logging

def logger(func):
    """A decorator that logs the function signature and return value."""
    @functools.wraps(func)
    def wrapper_logger(*args, **kwargs):
        args_repr = [repr(a) for a in args]
        kwargs_repr = [f"{k}={v!r}" for k, v in kwargs.items()]
        signature = ", ".join(args_repr + kwargs_repr)
        logging.debug(f"Calling {func.__name__}({signature})")
        value = func(*args, **kwargs)
        logging.debug(f"{func.__name__!r} returned {value!r}")
        return value
    return wrapper_logger
