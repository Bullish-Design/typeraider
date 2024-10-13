# app/utils/logger.py
import logging
import inspect
from inspect import getclasstree
import sys
import os
from pydantic import BaseModel, Field
from logging.handlers import RotatingFileHandler
from types import ModuleType, FunctionType
from typing import List, Dict, Any, Optional, Callable, Tuple
from typing_extensions import TypedDict
import functools
from datetime import datetime
from pprint import pformat

# Import the IntermediateResponse model
# from ..llm.agents.base.base import LLMResponse  # , IntermediateResponse

# Variables:
logdir = "log/logs"

MORE_WRAPPER_ASSIGNMENTS = (
    "__module__",
    "__name__",
    "__qualname__",
    "__annotations__",
    "__doc__",
    "__defaults__",
    "__kwdefaults__",
)

"""
class IntermediateResponse(BaseModel):
    function: str
    model_type: Any
    timestamp: datetime
    input: Any
    output: Any
    function_version: Optional[Any] = None
"""


# Misc Useful Functions:
def indent_level(level: int):
    indent = "  " * level
    return indent


def log_type(logger: logging.Logger, result: Any, level: int = 10) -> None:
    """
    Log results based on their type, performing any necessary modifications.

    Args:
    logger (logging.Logger): The logger object to use for logging.
    result (Any): The object to be logged.
    level (str): The logging level to use. Default is "info".
    """
    log_func = logger.info  # getattr(logger, level.lower())
    indent = "    " * level
    if result is None:
        log_func(f"{indent}Result: None")
    elif isinstance(result, (str, int, float, bool)):
        log_func(f"{indent}Result: {result}")
    elif isinstance(result, (list, tuple)):
        log_func(f"{indent}Result (length: {len(result)}):\n{pformat(result)}")
    elif isinstance(result, dict):
        log_func(f"{indent}Result (keys: {len(result)}):\n{pformat(result)}")
    elif hasattr(result, "__dict__"):
        # For custom objects, log their __dict__ representation
        log_func(
            f"{indent}Result (type: {type(result).__name__}):\n{pformat(result.__dict__)}"
        )
    else:
        # For any other types, use str() representation
        log_func(f"{indent}Result (type: {type(result).__name__}): {str(result)}")


def analyze_call_stack(logger: logging.Logger, level=0):
    # Define indent strings
    indent = indent_level(level)
    log_prefix = {
        "info": f"{indent}[CALL STACK] ",
        "debug": f"{indent}    [DETAIL] ",
    }
    logger.info(f"\n\n\nCall Stack:\n\n")
    logger.info(f"{indent}Starting call stack analysis (Level: {level})")
    called_entities = set()
    entity_list = []
    # Get the current frame
    current_frame = sys._getframe().f_back

    while current_frame:
        # Get information about the current frame
        frame_info = inspect.getframeinfo(current_frame)
        logger.info(f"{indent_level(level)}Frame Info: {frame_info}")
        # Get the code object for the frame
        code_obj = current_frame.f_code
        logger.info(f"{indent_level(level)}  Code Obj: {code_obj}")

        # Add function name to the set
        func_name = code_obj.co_name
        called_entities.add(func_name)
        entity_list.append(func_name)
        logger.info(f"{indent_level(level)}    Found function: {func_name}")
        logger.info(
            f"{indent_level(level)}            Locals: \n\n\n{current_frame.f_locals}\n\n"
        )
        for key, value in current_frame.f_locals.items():
            logger.info(f"{indent_level(level)}                   {key}: {value}")

        # Check if this is a method of a class
        if "self" in current_frame.f_locals:
            class_name = current_frame.f_locals["self"].__class__.__name__
            method_name = f"{class_name}.{func_name}"
            called_entities.add(method_name)
            entity_list.append(method_name)
            logger.info(f"{indent_level(level)}    Found method: {method_name}")

        # Log the filename and line number
        # logger.info(
        #    f"{log_prefix['debug']}In file: {frame_info.filename}, line: {frame_info.lineno}"
        # )

        # Move to the previous frame
        level += 2
        current_frame = current_frame.f_back

    result = sorted(called_entities)
    entity_result = entity_list
    logger.info(
        f"{log_prefix['info']}Call stack analysis complete. Found {len(result)} unique calls."
    )
    logger.info(f"{log_prefix['debug']}Called entities: {result}")
    logger.info(f"{log_prefix['debug']}Called entity list: {entity_result}")

    return result


def analyze_call_stack2(
    logger: logging.Logger, level: int = 0
) -> Tuple[List[str], List[Tuple[str, Optional[object], Optional[object]]]]:
    indent = indent_level(level)
    log_prefix = {
        "info": f"{indent}[CALL STACK] ",
        "debug": f"{indent}    [DETAIL] ",
    }

    logger.info("\n\n\nCall Stack:\n\n")
    logger.info(f"{indent}Starting call stack analysis (Level: {level})")

    called_entities: Set[str] = set()
    entity_list: List[str] = []
    instance_list: List[Tuple[str, Optional[object], Optional[object]]] = []

    current_frame = sys._getframe().f_back

    while current_frame:
        frame_info = inspect.getframeinfo(current_frame)
        logger.info(f"{indent}Frame Info: {frame_info}")

        code_obj = current_frame.f_code
        logger.info(f"{indent}  Code Obj: {code_obj}")

        func_name = code_obj.co_name
        called_entities.add(func_name)
        entity_list.append(func_name)

        logger.info(f"{indent}    Found function: {func_name}")
        logger.info(f"{indent}    Locals:")

        func_instance = None
        class_instance = None

        for key, value in current_frame.f_locals.items():
            logger.info(f"{indent}      {key}: {value}")
            if key == "self":
                class_instance = value
            elif callable(value) and value.__name__ == func_name:
                func_instance = value

        if "self" in current_frame.f_locals:
            class_name = current_frame.f_locals["self"].__class__.__name__
            method_name = f"{class_name}.{func_name}"
            called_entities.add(method_name)
            entity_list.append(method_name)
            logger.info(f"{indent}    Found method: {method_name}")

        instance_list.append((func_name, func_instance, class_instance))

        logger.info(f"{indent}    Function instance: {func_instance}")
        logger.info(f"{indent}    Class instance: {class_instance}")

        level += 2
        current_frame = current_frame.f_back

    result = sorted(called_entities)
    logger.info(
        f"{log_prefix['info']}Call stack analysis complete. Found {len(result)} unique calls."
    )
    logger.info(f"{log_prefix['debug']}Called entities: {result}")
    logger.info(f"{log_prefix['debug']}Called entity list: {entity_list}")
    logger.info(f"{log_prefix['debug']}Instance list: {instance_list}")

    return result, instance_list


def classtree(cls, indent=0, fillchar="-"):
    """
    Print class tree
    Args:
        cls: base class
        indent: indent size
        fillchar: fill char of indent
    """
    classes = subclasses(cls)
    tree = getclasstree(classes)
    print_tree(tree, indent, fillchar)


def fullname(cls):
    """Get fullname of cls"""
    if cls.__module__ in ["builtins", "exceptions"]:
        return cls.__name__
    return cls.__module__ + "." + cls.__name__


def subclasses(cls):
    """Get all sub classes of cls and itself"""
    result = set()
    todos = [cls]
    while todos:
        cls = todos.pop()
        for subcls in cls.__subclasses__():
            if subcls is not type and subcls not in result:
                result.add(subcls)
                todos.append(subcls)
    return result


def print_tree(tree, indent=0, fillchar="-"):
    """Print the return value of inspect.getclasstree"""
    for entry in tree:
        if isinstance(entry, tuple):
            cls, bases = entry
            cls_name = fullname(cls)
            filling = fillchar * indent
            if len(bases) < 2:
                print(filling + cls_name)
            else:
                bases_name = ",".join([fullname(x) for x in bases])
                print(filling + "{}({})".format(cls_name, bases_name))
        else:
            print_tree(entry, indent + 4, fillchar)


def log_tree(logger: logging.Logger, tree, indent=0, fillchar="-"):
    """Print the return value of inspect.getclasstree"""
    # print(f"\n\n\n\n\n\n\n\n\n\n\n\nLogging Tree:\n\n\n\n\n")
    for entry in tree:
        filling = fillchar * indent
        print(f"{filling} {entry}")
        if isinstance(entry, tuple):
            cls, bases = entry
            cls_name = fullname(cls)
            filling = fillchar * indent
            if len(bases) < 2:
                # print(filling + cls_name)
                logger.info(f"| {filling} {cls_name}")
            else:
                bases_name = ",".join([fullname(x) for x in bases])
                logger.info(f"| {filling} {cls_name}({bases_name})")
                # print(filling + "{}({})".format(cls_name, bases_name))
        else:
            log_tree(logger, entry, indent + 4, fillchar)
    # print(f"\n\n\n\n\n\n\nFinished Logging Tree:\n\n\n\n\n\n\n\n\n\n\n\n")


def inspect_code_state(logger: logging.Logger, context: Any = None):
    logger.info("")
    logger.info("")
    start_str = """


                                **************************************************************
                                **************************************************************
                                **************************************************************
                                         Starting Comprehensive Code State Inspection
                                **************************************************************
                                **************************************************************
                                **************************************************************


    """
    # logger.info("********************************************")
    # logger.info("********************************************")
    # logger.info("********************************************")
    # logger.info("Starting comprehensive code state inspection")
    # logger.info("********************************************")
    # logger.info("********************************************")
    # logger.info("********************************************\n\n")
    logger.info(f"{start_str}\n\n")
    # Inspect the call stack
    logger.info("Call Stack:")
    for frame_info in inspect.stack()[1:]:  # Skip this function's frame
        logger.info(
            f"Call Stack | File '{frame_info.filename}', line {frame_info.lineno}, in {frame_info.function}"
        )
        if frame_info.code_context:
            logger.info(f"              {frame_info.code_context[0].strip()}")

    # Inspect the current module
    current_module = inspect.getmodule(inspect.currentframe())
    logger.info(f"Current Module: {current_module.__name__}")

    # Inspect global variables
    logger.info("Global Variables:")
    for name, value in current_module.__dict__.items():
        if not name.startswith("__"):
            logger.info(f"Global Variables |  {name}: {type(value)}")

    # Inspect local variables if context is provided
    if context:
        logger.info("Local Variables:")
        local_vars = {}
        if isinstance(context, dict):
            local_vars = context
        elif hasattr(context, "__dict__"):
            local_vars = context.__dict__
        for name, value in local_vars.items():
            logger.info(f"Local Variables |    {name}: {type(value)}")

    # Inspect loaded modules
    logger.info("Loaded Modules:")
    for name, module in sys.modules.items():
        if module:
            logger.info(f"Loaded Modules |    {name}: {module.__name__}")

    # Inspect defined functions in the current module
    logger.info(
        "\n\n------------------------------------------------ \n                   Defined Functions:\n------------------------------------------------ \n"
    )
    for name, value in current_module.__dict__.items():
        if isinstance(value, FunctionType):
            logger.info(f"Function | -------------- {name} ----------------")
            # logger.info(f"  {name}:")
            logger.info(f"Function |      Arguments: {inspect.signature(value)}")
            logger.info(f"Function |         Module: {inspect.getmodule(value)}")

    # Inspect defined classes in the current module
    class_list = []
    logger.info("Defined Classes:")
    for name, value in current_module.__dict__.items():
        if inspect.isclass(value):
            class_list.append(value)
            logger.info(f"Defined Classes |    {name}:")
            logger.info(f"Defined Classes |       Base classes: {value.__bases__}")
            logger.info(
                f"Defined Classes |          Docstring: {inspect.getdoc(value)}"
            )
            for method_name, method in inspect.getmembers(
                value, predicate=inspect.isfunction
            ):
                logger.info(f"Defined Classes |          Method {method_name}:")
                logger.info(
                    f"Defined Classes |              Arguments: {inspect.signature(method)}"
                )

    class_tree = inspect.getclasstree(class_list)
    logger.info(
        f"\n\n\n                                           ************** Logging Class Tree **************\n\n"
    )
    print(f"\n\n\n\n\n\n\n\n\n\n\n\nLogging Tree:\n\n\n\n\n")

    # logger.info(f"Class Tree:\n\n\n{class_tree}\n\n")
    # print_tree(class_tree)
    log_tree(logger, class_tree)
    print(f"\n\n\n\n\n\n\n\n\n\n\n\nFinished Logging Tree:\n\n\n\n\n")

    logger.info("Code state inspection complete\n\n\n")


def log_args_and_kwargs(
    func_name: str, logger: logging.Logger, args: tuple, kwargs: dict
):
    logger.info(f"Logging arguments and keyword arguments for function: {func_name}")
    for i, arg in enumerate(args):
        logger.info(f"Arg {i}: {type(arg)}\n\n{arg}\n")
    for key, value in kwargs.items():
        logger.info(f"Kwarg {key}: {type(value)}\n\n{value}\n")


def log_func(logger, func):
    logger.info(f"Logging function dictionary for: {func.__name__}")
    for k, v in func.__dict__.items():
        logger.info(f"    Key: {k} ==> Val type: {type(v)} ==> Val: {v}")


def log_output(logger: logging.Logger, state_logger: logging.Logger):
    intermediate_class_list = []

    # logger = logging.getLogger(logger_name)
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func, assigned=MORE_WRAPPER_ASSIGNMENTS)
        def wrapper(*args, **kwargs):
            # inspect_code_state(state_logger, locals())
            # analyze_call_stack(state_logger)

            # Log the function info
            # log_func(logger, func)
            # Log all arguments
            # log_args_and_kwargs(func.__name__, logger, args, kwargs)

            # Prepare input data
            input_data = {"args": args, "kwargs": kwargs}
            current_time = datetime.now()
            # Call the original function
            result = func(*args, **kwargs)

            # Prepare log message
            log_message = (
                f"\n\nFunction: {func.__name__}\n"
                f"Timestamp: {current_time}\n"
                f"Input: {input_data}\n"
                f"Output: {result}\n"
            )
            if hasattr(result, "metadata"):
                function_version = result.metadata
            else:
                function_version = None
            if function_version:
                log_message += f"Version: {function_version}\n"

            # intermediate_step = IntermediateResponse(
            #    function=func.__name__,
            #    input=input_data,
            #    output=result,
            #    timestamp=current_time,
            #    function_version=function_version,
            # )
            # stack_result, stack_instances = analyze_call_stack2(state_logger)

            # logger.info("\n\n\n**************** Stack Results *******************\n")
            # for result_item in stack_result:
            #    log_result = result_item
            #    log_type(logger, log_result)

            # logger.info("\n\n\n**************** Stack Instances *******************\n")
            # for result_item in stack_instances:
            #    log_result = result_item
            #    log_type(logger, log_result)

            # Log the message
            logger.info(log_message)
            # if args:
            #    logger.info(args)

            # Find the SoftwareArchitect instance
            # software_architect_instance = None

            # len_args = len(args)
            # logger.info(f"{len_args} Instance Args:")
            # arg_count = 0
            #    for arg in args:
            # for arg in args:
            #    # arg_count += 1
            #    # logger.info(f"    Arg {arg_count}: {arg} ")

            #    if isinstance(arg, BaseModel) and hasattr(arg, "intermediate_steps"):
            #        #    if hasattr(arg, "intermediate_steps"):
            #        software_architect_instance = arg
            #        break

            # if not software_architect_instance:
            #    len_kwargs = len(kwargs.values())
            #    # logger.info(f"{len_kwargs} Instance Kwargs:")
            #    kwarg_count = 0
            #    for arg in kwargs.values():
            #        # kwarg_count += 1
            #        # logger.info(f"    Kwarg {kwarg_count}: {arg}")
            #        # if isinstance(arg, BaseModel) and hasattr(
            #        #    arg, "intermediate_steps"
            #        # ):
            #        if hasattr(arg, "intermediate_steps"):
            #            software_architect_instance = arg
            #            break

            ## If we found a SoftwareArchitect instance, add the intermediate step
            # if software_architect_instance:
            #    logger.info(f"Grabbing instance: \n\n{software_architect_instance}\n")
            #    if not hasattr(software_architect_instance, "intermediate_steps"):
            #        software_architect_instance.intermediate_steps = []
            #    software_architect_instance.intermediate_steps.append(intermediate_step)
            #    logger.info(
            #        f"Current intermediate steps: {software_architect_instance.intermediate_steps}"
            #    )
            # else:
            #    logger.warning(
            #        f"No SoftwareArchitect instance found for function: {func.__name__}"
            #    )
            # mro = inspect.getmro(func)
            # logger.warning(f"\n\n\n\n\nMRO:\n\n{mro}\n\n\n\n\n")

            return result

        # test_ans = wrapper(*args)  # wrapper(*args, **kwargs)
        # if hasattr(result, "intermediate_steps"):
        #    logger.warning(f"\n\n\nFOUND IT!!!\n\n\n{result}\n\n\n")
        # logger.warning(f"\n\n\nTest Answer Result:\n\n{test_ans}\n")
        return wrapper
        # analyze_call_stack(state_logger)

    # test_ans2 = decorator(func)
    # logger.warning(f"\nTest Answer 2 Result:\n\n{test_ans2}\n\n")

    return decorator


def get_logger(name, stream=False):
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    # Create logs directory if it doesn't exist
    if not os.path.exists(logdir):
        os.makedirs(logdir)

    # Create file handler
    file_handler = RotatingFileHandler(
        f"{logdir}/{name}.log",
        maxBytes=1024 * 1024 * 10,  # 10MB
        backupCount=5,
    )
    file_handler.setLevel(logging.DEBUG)

    # Create formatter and add it to the handlers
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    # Create console handler
    if stream:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    file_handler.setFormatter(formatter)

    # Add the handlers to the logger
    logger.addHandler(file_handler)

    for i in range(2):
        logger.info("")
    logger.info(
        f"\n\n\n\n\n**************** {name} Logger initialized ****************\n\n\n\n"
    )
    logger.info("")
    return logger
