# args_handler.py

import sys
import os
from pathlib import Path
from aider.args import get_parser
from aider.init_utils import check_config_files_for_yes, load_dotenv_files, get_git_root
from aider.llm import litellm  # Ensure litellm is loaded
from prompt_toolkit.enums import EditingMode
import httpx


class ArgsHandler:
    def __init__(self, argv=None, force_git_root=None):
        self.argv = argv or sys.argv[1:]
        self.force_git_root = force_git_root
        self.git_root = None
        self.args = None
        self.parser = None
        self.editing_mode = None
        self.loaded_dotenvs = []

    def parse_arguments(self):
        # Determine git root
        self.git_root = self.force_git_root or get_git_root()

        # Get default config files
        conf_fname = Path(".aider.conf.yml")
        default_config_files = self.get_default_config_files(conf_fname)

        # Initial argument parsing
        self.parser = get_parser(default_config_files, self.git_root)
        try:
            self.args, unknown = self.parser.parse_known_args(self.argv)
        except AttributeError as e:
            if all(
                word in str(e)
                for word in ["bool", "object", "has", "no", "attribute", "strip"]
            ):
                if check_config_files_for_yes(default_config_files):
                    return 1
            raise e

        # Reverse config files for precedence
        default_config_files.reverse()
        self.parser = get_parser(default_config_files, self.git_root)
        self.args, unknown = self.parser.parse_known_args(self.argv)

        # Load .env files
        self.loaded_dotenvs = load_dotenv_files(
            self.git_root, self.args.env_file, self.args.encoding
        )

        # Re-parse arguments to include any new args from .env
        self.args = self.parser.parse_args(self.argv)

        # Handle SSL verification
        if not self.args.verify_ssl:
            os.environ["SSL_VERIFY"] = ""
            litellm._load_litellm()
            litellm._lazy_module.client_session = httpx.Client(verify=False)
            litellm._lazy_module.aclient_session = httpx.AsyncClient(verify=False)

        # Handle color themes
        self.handle_color_themes()

        # Set editing mode
        self.editing_mode = EditingMode.VI if self.args.vim else EditingMode.EMACS

        return None

    def get_default_config_files(self, conf_fname):
        default_config_files = []
        try:
            default_config_files += [conf_fname.resolve()]  # CWD
        except OSError:
            pass

        if self.git_root:
            git_conf = Path(self.git_root) / conf_fname  # Git root
            if git_conf not in default_config_files:
                default_config_files.append(git_conf)
        default_config_files.append(Path.home() / conf_fname)  # Home directory
        default_config_files = list(map(str, default_config_files))
        return default_config_files

    def handle_color_themes(self):
        if self.args.dark_mode:
            self.args.user_input_color = "#32FF32"
            self.args.tool_error_color = "#FF3333"
            self.args.tool_warning_color = "#FFFF00"
            self.args.assistant_output_color = "#00FFFF"
            self.args.code_theme = "monokai"

        if self.args.light_mode:
            self.args.user_input_color = "green"
            self.args.tool_error_color = "red"
            self.args.tool_warning_color = "#FFA500"
            self.args.assistant_output_color = "blue"
            self.args.code_theme = "default"
