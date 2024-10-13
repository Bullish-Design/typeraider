# An attempt to wrap the existing call to litellm in order to use mirascope for structured calls.
# Should default back to a plain call if a typed call is not found.
#      - Or default to passing back the plain response?
#      - Or default to restructuring the plain response and passig that?

import functools
import json
import os
import inspect
import logging
from collections.abc import Generator, Iterator
from datetime import datetime
from .log.logger import get_logger


logger = get_logger("coder_class_wrapper")

# Variables:
logdir = "log/logs"

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


class OverwritingFileHandler(logging.FileHandler):
    """
    Custom logging handler that can overwrite the last log entry.
    """

    def __init__(self, filename, mode="a", encoding=None, delay=False):
        super().__init__(filename, mode, encoding, delay)
        self.last_record_position = None
        self.overwrite_last = False

    def emit(self, record):
        try:
            if self.stream is None:
                self.stream = self._open()

            if not self.overwrite_last or self.last_record_position is None:
                # Record the current file position before writing
                self.last_record_position = self.stream.tell()
            else:
                # Seek back to the last record position
                self.stream.seek(self.last_record_position)
                # Truncate the file to the current position
                self.stream.truncate()

            msg = self.format(record)
            stream = self.stream
            stream.write(msg + self.terminator)
            # Flush to ensure the message is written
            self.flush()
        except Exception:
            self.handleError(record)


def get_function_logger(func_name):
    """
    Creates a logger for a specific function/method, writing to its own logfile.
    """
    logdir = "log/logs"

    logger = logging.getLogger(func_name)
    logger.setLevel(logging.INFO)
    if not logger.handlers:
        splitname = func_name.split(".")
        if len(splitname) > 1:
            # Nested function, create a subdirectory for the log
            new_logdir = f"{logdir}/{splitname[0]}"
            if not os.path.exists(new_logdir):
                os.makedirs(new_logdir)
            func_name = splitname[-1]
            logdir = new_logdir
        log_filename = f"{logdir}/{func_name}.log"
        handler = OverwritingFileHandler(log_filename)
        formatter = logging.Formatter("%(asctime)s:%(levelname)s:%(message)s")
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    else:
        handler = logger.handlers[0]
    return logger, handler


class GeneratorLogger:
    """
    A wrapper for generators to control logging of streamed results.
    """

    def __init__(self, gen, func_name, logger, handler):
        self.gen = gen
        self.func_name = func_name
        self.logger = logger
        self.handler = handler
        self.count = 0
        self.prev_value = None
        self.handler.overwrite_last = False
        self.logger.info(f"{self.func_name} returned a generator")

    def __iter__(self):
        return self

    def __next__(self):
        try:
            value = next(self.gen)
            self.count += 1

            if self.count == 1:
                # First value, always log
                self.prev_value = value
                self.handler.overwrite_last = False
                self.logger.info(
                    f"{self.func_name} yielded value #{self.count}: {value}"
                )
            else:
                if (
                    isinstance(value, str)
                    and isinstance(self.prev_value, str)
                    and value.startswith(self.prev_value)
                ):
                    # New value is just appending to previous
                    self.handler.overwrite_last = True
                    self.logger.info(
                        f"{self.func_name} yielded value #{self.count}: {value}"
                    )
                else:
                    # Output is different, log as new entry
                    self.handler.overwrite_last = False
                    self.logger.info(
                        f"{self.func_name} yielded value #{self.count}: {value}"
                    )
                self.prev_value = value
            return value
        except StopIteration:
            self.handler.overwrite_last = False
            self.logger.info(
                f"{self.func_name} generator exhausted after yielding {self.count} items."
            )
            raise


def log_function_call(func):
    """
    Decorator to log the input arguments and output of a function.
    """

    def wrapper(*args, **kwargs):
        logger, handler = get_function_logger(func.__qualname__)
        logger.info(f"Calling {func.__qualname__} with args={args}, kwargs={kwargs}")
        result = func(*args, **kwargs)
        if isinstance(result, (Generator, Iterator)) or inspect.isgenerator(result):
            # Wrap the generator to control logging
            return GeneratorLogger(result, func.__qualname__, logger, handler)
        else:
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
