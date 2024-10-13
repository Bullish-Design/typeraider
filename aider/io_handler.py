# io_handler.py

from aider.io import InputOutput
from prompt_toolkit.enums import EditingMode


class IOHandler:
    def __init__(self, args, input=None, output=None):
        self.args = args
        self.input = input
        self.output = output
        self.io = None

    def setup_io(self):
        def get_io(pretty):
            return InputOutput(
                pretty,
                self.args.yes_always,
                self.args.input_history_file,
                self.args.chat_history_file,
                input=self.input,
                output=self.output,
                user_input_color=self.args.user_input_color,
                tool_output_color=self.args.tool_output_color,
                tool_warning_color=self.args.tool_warning_color,
                tool_error_color=self.args.tool_error_color,
                completion_menu_color=self.args.completion_menu_color,
                completion_menu_bg_color=self.args.completion_menu_bg_color,
                completion_menu_current_color=self.args.completion_menu_current_color,
                completion_menu_current_bg_color=self.args.completion_menu_current_bg_color,
                assistant_output_color=self.args.assistant_output_color,
                code_theme=self.args.code_theme,
                dry_run=self.args.dry_run,
                encoding=self.args.encoding,
                llm_history_file=self.args.llm_history_file,
                editingmode=EditingMode.VI if self.args.vim else EditingMode.EMACS,
            )

        self.io = get_io(self.args.pretty)
        try:
            self.io.rule()
        except UnicodeEncodeError as err:
            if not self.io.pretty:
                raise err
            self.io = get_io(False)
            self.io.tool_warning(
                "Terminal does not support pretty output (UnicodeDecodeError)"
            )

        return self.io
