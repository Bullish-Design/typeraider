from .ask_prompts import AskPrompts
from .base_coder import Coder
from ..llm_wrapper import log_methods


@log_methods
class AskCoder(Coder):
    """Ask questions about code without making any changes."""

    edit_format = "ask"
    gpt_prompts = AskPrompts()
