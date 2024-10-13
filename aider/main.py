# main.py

import sys
import os
import json
from pathlib import Path
from aider.report import report_uncaught_exceptions
from aider.coders import Coder
from aider.commands import Commands, SwitchCoder
from aider import utils
from aider.versioncheck import check_version
from aider.init_utils import check_streamlit_install, launch_gui, register_models, register_litellm_models


# Import our new handlers
from aider.args_handler import ArgsHandler
from aider.io_handler import IOHandler
from aider.git_handler import GitHandler
from aider.coder_initializer import CoderInitializer

"""
def initialize_main_model(args, io, git_root):
    # Set API keys from args
    if args.anthropic_api_key:
        os.environ["ANTHROPIC_API_KEY"] = args.anthropic_api_key

    if args.openai_api_key:
        os.environ["OPENAI_API_KEY"] = args.openai_api_key
    if args.openai_api_base:
        os.environ["OPENAI_API_BASE"] = args.openai_api_base
    if args.openai_api_version:
        os.environ["OPENAI_API_VERSION"] = args.openai_api_version
    if args.openai_api_type:
        os.environ["OPENAI_API_TYPE"] = args.openai_api_type
    if args.openai_organization_id:
        os.environ["OPENAI_ORGANIZATION"] = args.openai_organization_id

    # Register models
    register_models(git_root, args.model_settings_file, io, verbose=args.verbose)
    register_litellm_models(git_root, args.model_metadata_file, io, verbose=args.verbose)

    # Initialize main model
    if not args.model:
        args.model = "gpt-4o-2024-08-06"
        if os.environ.get("ANTHROPIC_API_KEY"):
            args.model = "claude-3-5-sonnet-20240620"

    main_model = models.Model(
        args.model,
        weak_model=args.weak_model,
        editor_model=args.editor_model,
        editor_edit_format=args.editor_edit_format,
    )

    if args.verbose:
        io.tool_output("Model info:")
        io.tool_output(json.dumps(main_model.info, indent=4))

    return main_model


def handle_version_checks(args, io):
    if args.just_check_update:
        update_available = check_version(io, just_check=True, verbose=args.verbose)
        return 0 if not update_available else 1

    if args.install_main_branch:
        success = install_from_main_branch(io)
        return 0 if success else 1

    if args.upgrade:
        success = install_upgrade(io)
        return 0 if success else 1

    if args.check_update:
        check_version(io, verbose=args.verbose)

    if args.list_models:
        models.print_matching_models(io, args.list_models)
        return 0

    return None
"""


def main(argv=None, input=None, output=None, force_git_root=None, return_coder=False):
    # Initialize logging or any other startup tasks
    report_uncaught_exceptions()

    # Argument handling
    args_handler = ArgsHandler(argv=argv, force_git_root=force_git_root)
    exit_code = args_handler.parse_arguments()
    if exit_code is not None:
        sys.exit(exit_code)

    args = args_handler.args
    git_root = args_handler.git_root

    # IO handling
    io_handler = IOHandler(args, input=input, output=output)
    io = io_handler.setup_io()

    # Handle GUI mode
    if args.gui and not return_coder:
        # from aider.utils import check_streamlit_install, launch_gui

        if not check_streamlit_install(io):
            sys.exit(1)
        launch_gui(args_handler.argv)
        sys.exit(0)

    # Process files
    all_files = args.files + (args.file or [])
    fnames = [str(Path(fn).resolve()) for fn in all_files]
    read_only_fnames = [str(Path(fn).resolve()) for fn in (args.read or [])]

    # Handle directories
    git_dname = None
    if len(all_files) == 1 and Path(all_files[0]).is_dir():
        if args.git:
            git_dname = str(Path(all_files[0]).resolve())
            fnames = []
        else:
            io.tool_error(f"{all_files[0]} is a directory, but --no-git selected.")
            sys.exit(1)

    # Reparse if necessary
    if args.git and not force_git_root:
        from aider.init_utils import guessed_wrong_repo

        right_repo_root = guessed_wrong_repo(io, git_root, fnames, git_dname)
        if right_repo_root:
            return main(argv, input, output, right_repo_root, return_coder=return_coder)
    
    ## Handle version checks
    #exit_code = handle_version_checks(args, io)
    #if exit_code is not None:
    #    sys.exit(exit_code)

    # Coder initialization (includes version checks and model initialization)
    coder_initializer = CoderInitializer(args, io, git_root, None, fnames, read_only_fnames)
    exit_code = coder_initializer.initialize_coder()
    if exit_code is not None:
        sys.exit(exit_code)

    # Now that main_model is initialized, we can initialize GitHandler
    main_model = coder_initializer.main_model

    # Git handling
    git_handler = GitHandler(args, io, git_root, fnames, git_dname, main_model)
    exit_code = git_handler.initialize_git()
    if exit_code is not None:
        sys.exit(exit_code)

    # Update repo in coder_initializer
    coder_initializer.repo = git_handler.repo

    # Re-initialize the coder with the repo
    exit_code = coder_initializer.create_coder()
    if exit_code is not None:
        sys.exit(exit_code)

    coder = coder_initializer.coder

    if return_coder:
        return coder

    # Now proceed with the main loop or other operations

    coder.show_announcements()

    if args.show_prompts:
        coder.cur_messages += [
            dict(role="user", content="Hello!"),
        ]
        messages = coder.format_messages().all_messages()
        utils.show_messages(messages)
        return

    # Handling of various args and commands

    if args.lint:
        coder.commands.cmd_lint(fnames=fnames)

    if args.test:
        if not args.test_cmd:
            io.tool_error("No --test-cmd provided.")
            sys.exit(1)
        test_errors = coder.commands.cmd_test(args.test_cmd)
        if test_errors:
            coder.run(test_errors)

    if args.commit:
        if args.dry_run:
            io.tool_output("Dry run enabled, skipping commit.")
        else:
            coder.commands.cmd_commit()

    if args.lint or args.test or args.commit:
        return

    if args.show_repo_map:
        repo_map = coder.get_repo_map()
        if repo_map:
            io.tool_output(repo_map)
        return

    if args.apply:
        content = io.read_text(args.apply)
        if content is None:
            return
        coder.partial_response_content = content
        coder.apply_updates()
        return

    if "VSCODE_GIT_IPC_HANDLE" in os.environ:
        args.pretty = False
        io.tool_output("VSCode terminal detected, pretty output has been disabled.")

    io.tool_output(
        'Use /help <question> for help, run "aider --help" to see cmd line args'
    )

    if git_root and Path.cwd().resolve() != Path(git_root).resolve():
        io.tool_warning(
            "Note: in-chat filenames are always relative to the git working dir, not the current"
            " working dir."
        )

        io.tool_output(f"Current working dir: {Path.cwd()}")
        io.tool_output(f"Git working dir: {git_root}")

    if args.message:
        io.add_to_input_history(args.message)
        io.tool_output()
        try:
            coder.run(with_message=args.message)
        # except SwitchCoder:
        #    pass
        except ValueError as e:
            io.tool_error(f"Coder Run Error: {e}")
        return

    if args.message_file:
        try:
            message_from_file = io.read_text(args.message_file)
            io.tool_output()
            coder.run(with_message=message_from_file)
        except FileNotFoundError:
            io.tool_error(f"Message file not found: {args.message_file}")
            sys.exit(1)
        except IOError as e:
            io.tool_error(f"Error reading message file: {e}")
            sys.exit(1)
        return

    if args.exit:
        return

    while True:
        try:
            coder.run()
            return
        except SwitchCoder as switch:
            kwargs = dict(io=io, from_coder=coder)
            kwargs.update(switch.kwargs)
            if "show_announcements" in kwargs:
                del kwargs["show_announcements"]

            coder = Coder.create(**kwargs)

            if switch.kwargs.get("show_announcements") is not False:
                coder.show_announcements()


if __name__ == "__main__":
    main()
