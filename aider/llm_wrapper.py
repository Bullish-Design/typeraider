# An attempt to wrap the existing call to litellm in order to use mirascope for structured calls.
# Should default back to a plain call if a typed call is not found.
#      - Or default to passing back the plain response?
#      - Or default to restructuring the plain response and passig that?

import functools
import json
from datetime import datetime
from ..log.logger import get_logger

logger = get_logger("llm_wrapper")


def log_io_to_file(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        func_name = func.__name__

        input_log = (
            f"[{timestamp}] {func_name} - Inputs: {json.dumps(kwargs, default=str)}\n"
        )
        logger.info(input_log)
        result = func(*args, **kwargs)

        output_log = (
            f"[{timestamp}] {func_name} - Outputs: {json.dumps(result, default=str)}\n"
        )
        logger.debug(output_log)
        with open("litellm_io_log.log", "a") as f:
            f.write(input_log)
            f.write(output_log)

        return result

    return wrapper


class LiteLLMLogger:
    def __init__(self, litellm_instance):
        self.litellm = litellm_instance

    @log_io_to_file
    def completion(self, *args, **kwargs):
        return self.litellm.completion(*args, **kwargs)

    @log_io_to_file
    def embedding(self, *args, **kwargs):
        return self.litellm.embedding(*args, **kwargs)
