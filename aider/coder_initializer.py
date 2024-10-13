# coder_initializer.py

import os
import sys
import json
from aider import models
from aider.coders import Coder
from aider.init_utils import (
    register_models,
    register_litellm_models,
    parse_lint_cmds,
    check_and_load_imports,
    scrub_sensitive_info,
)
from aider.commands import Commands
from aider.history import ChatSummary
from aider.versioncheck import (
    check_version,
    install_from_main_branch,
    install_upgrade,
)


class CoderInitializer:
    def __init__(self, args, io, git_root, repo, fnames, read_only_fnames):
        self.args = args
        self.io = io
        self.git_root = git_root
        self.repo = repo
        self.fnames = fnames
        self.read_only_fnames = read_only_fnames
        self.main_model = None
        self.coder = None
        self.commands = None
        self.summarizer = None
        self.lint_cmds = None

    def initialize_coder(self):
        # Handle version checks
        exit_code = self.handle_version_checks()
        if exit_code is not None:
            return exit_code

        # Load models and initialize main_model
        exit_code = self.initialize_main_model()
        if exit_code is not None:
            return exit_code

        # Parse lint commands
        self.lint_cmds = parse_lint_cmds(self.args.lint_cmd, self.io)
        if self.lint_cmds is None:
            return 1

        # Initialize commands and summarizer
        self.commands = Commands(
            self.io,
            None,
            verify_ssl=self.args.verify_ssl,
            args=self.args,
            parser=None,
            verbose=self.args.verbose,
        )

        self.summarizer = ChatSummary(
            [self.main_model.weak_model, self.main_model],
            self.args.max_chat_history_tokens or self.main_model.max_chat_history_tokens,
        )

        # Initialize coder
        exit_code = self.create_coder()
        if exit_code is not None:
            return exit_code

        return None

    def handle_version_checks(self):
        if self.args.just_check_update:
            update_available = check_version(
                self.io, just_check=True, verbose=self.args.verbose
            )
            return 0 if not update_available else 1

        if self.args.install_main_branch:
            success = install_from_main_branch(self.io)
            return 0 if success else 1

        if self.args.upgrade:
            success = install_upgrade(self.io)
            return 0 if success else 1

        if self.args.check_update:
            check_version(self.io, verbose=self.args.verbose)

        if self.args.list_models:
            models.print_matching_models(self.io, self.args.list_models)
            return 0

        return None

    def initialize_main_model(self):
        cmd_line = " ".join(sys.argv)
        cmd_line = scrub_sensitive_info(self.args, cmd_line)
        self.io.tool_output(cmd_line, log_only=True)

        check_and_load_imports(self.io, verbose=self.args.verbose)

        # Set API keys from args
        if self.args.anthropic_api_key:
            os.environ["ANTHROPIC_API_KEY"] = self.args.anthropic_api_key

        if self.args.openai_api_key:
            os.environ["OPENAI_API_KEY"] = self.args.openai_api_key
        if self.args.openai_api_base:
            os.environ["OPENAI_API_BASE"] = self.args.openai_api_base
        if self.args.openai_api_version:
            os.environ["OPENAI_API_VERSION"] = self.args.openai_api_version
        if self.args.openai_api_type:
            os.environ["OPENAI_API_TYPE"] = self.args.openai_api_type
        if self.args.openai_organization_id:
            os.environ["OPENAI_ORGANIZATION"] = self.args.openai_organization_id

        # Register models
        register_models(
            self.git_root,
            self.args.model_settings_file,
            self.io,
            verbose=self.args.verbose,
        )
        register_litellm_models(
            self.git_root,
            self.args.model_metadata_file,
            self.io,
            verbose=self.args.verbose,
        )

        # Initialize main model
        if not self.args.model:
            self.args.model = "gpt-4o-2024-08-06"
            if os.environ.get("ANTHROPIC_API_KEY"):
                self.args.model = "claude-3-5-sonnet-20240620"

        self.main_model = models.Model(
            self.args.model,
            weak_model=self.args.weak_model,
            editor_model=self.args.editor_model,
            editor_edit_format=self.args.editor_edit_format,
        )

        if self.args.verbose:
            self.io.tool_output("Model info:")
            self.io.tool_output(json.dumps(self.main_model.info, indent=4))

        # Model warnings
        if self.args.show_model_warnings:
            problem = models.sanity_check_models(self.io, self.main_model)
            if problem:
                self.io.tool_output(
                    "You can skip this check with --no-show-model-warnings"
                )
                self.io.tool_output()
                try:
                    if not self.io.confirm_ask("Proceed anyway?"):
                        return 1
                except KeyboardInterrupt:
                    return 1

        return None

    def create_coder(self):
        if self.args.cache_prompts and self.args.map_refresh == "auto":
            self.args.map_refresh = "files"

        if not self.main_model.streaming:
            if self.args.stream:
                self.io.tool_warning(
                    f"Warning: Streaming is not supported by {self.main_model.name}. Disabling streaming."
                )
            self.args.stream = False

        try:
            self.coder = Coder.create(
                main_model=self.main_model,
                edit_format=self.args.edit_format,
                io=self.io,
                repo=self.repo,
                fnames=self.fnames,
                read_only_fnames=self.read_only_fnames,
                show_diffs=self.args.show_diffs,
                auto_commits=self.args.auto_commits,
                dirty_commits=self.args.dirty_commits,
                dry_run=self.args.dry_run,
                map_tokens=self.args.map_tokens,
                verbose=self.args.verbose,
                stream=self.args.stream,
                use_git=self.args.git,
                restore_chat_history=self.args.restore_chat_history,
                auto_lint=self.args.auto_lint,
                auto_test=self.args.auto_test,
                lint_cmds=self.lint_cmds,
                test_cmd=self.args.test_cmd,
                commands=self.commands,
                summarizer=self.summarizer,
                map_refresh=self.args.map_refresh,
                cache_prompts=self.args.cache_prompts,
                map_mul_no_files=self.args.map_multiplier_no_files,
                num_cache_warming_pings=self.args.cache_keepalive_pings,
                suggest_shell_commands=self.args.suggest_shell_commands,
                chat_language=self.args.chat_language,
            )
        except ValueError as err:
            self.io.tool_error(str(err))
            return 1

        return None
