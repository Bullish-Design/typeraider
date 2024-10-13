# An attempt to wrap the existing call to litellm in order to use mirascope for structured calls.
# Should default back to a plain call if a typed call is not found.
#      - Or default to passing back the plain response?
#      - Or default to restructuring the plain response and passig that?

import functools
import json
import inspect
from datetime import datetime
from .log.logger import get_logger

logger = get_logger("coder_class_wrapper")

logfilename = "llm_wrapper_log.log"


def log_io_to_file(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        func_name = func.__name__

        logger.info(
            f"Logging function {func_name} with: \n\nargs: {args}\nkwargs: {kwargs}\n"
        )
        # Check if this is a class method
        if len(args) > 0 and isinstance(args[0], type):
            # This is likely a class method, adjust args accordingly
            # logger.info(f"Detected class method, adjusting args: \n\n{args}\n")
            args = args[1:]
            logger.info(f"Detected class method - Adjusted args: \n\n{args}\n")

        input_log = (
            f"[{timestamp}] {func_name} - Inputs: {json.dumps(kwargs, default=str)}\n"
        )

        result = func(*args, **kwargs)

        output_log = (
            f"[{timestamp}] {func_name} - Outputs: {json.dumps(result, default=str)}\n"
        )

        with open(logfilename, "a") as f:
            f.write(input_log)
            f.write(output_log)

        return result

    return wrapper


def log_function_call(func):
    """
    Decorator to log the input arguments and output of a function.
    """

    def wrapper(*args, **kwargs):
        logger.info(f"Calling {func.__qualname__} with args={args}, kwargs={kwargs}")
        result = func(*args, **kwargs)
        logger.info(f"{func.__qualname__} returned {result}")
        return result

    return wrapper


def log_methods(cls):
    """
    Class decorator to wrap all methods of a class with logging.
    """
    for attr_name, attr_value in cls.__dict__.items():
        if isinstance(attr_value, staticmethod):
            original_func = attr_value.__func__
            decorated_func = log_function_call(original_func)
            setattr(cls, attr_name, staticmethod(decorated_func))
        elif isinstance(attr_value, classmethod):
            original_func = attr_value.__func__
            decorated_func = log_function_call(original_func)
            setattr(cls, attr_name, classmethod(decorated_func))
        elif inspect.isfunction(attr_value):
            original_func = attr_value
            decorated_func = log_function_call(original_func)
            setattr(cls, attr_name, decorated_func)
    return cls


class LiteLLMLogger:
    def __init__(self, litellm_instance):
        self.litellm = litellm_instance
        # Copy all attributes from the original instance
        for attr_name in dir(litellm_instance):
            if not attr_name.startswith("__"):
                attr = getattr(litellm_instance, attr_name)
                if isinstance(attr, classmethod):
                    # For class methods, we need to wrap them differently
                    setattr(self, attr_name, classmethod(log_io_to_file(attr.__func__)))
                else:
                    setattr(self, attr_name, attr)

    @log_io_to_file
    def completion(self, *args, **kwargs):
        return self.litellm.completion(*args, **kwargs)

    @log_io_to_file
    def embedding(self, *args, **kwargs):
        return self.litellm.embedding(*args, **kwargs)

    def __getattr__(self, name):
        # Fallback for any attributes or methods not explicitly defined
        return getattr(self.litellm, name)
