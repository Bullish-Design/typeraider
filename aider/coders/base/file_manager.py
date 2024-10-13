# file_manager.py

import os
from pathlib import Path
from aider.utils import is_image_file


class FileManager:
    def __init__(self, io, main_model):
        self.io = io
        self.main_model = main_model
        self.tracked_files = set()
        self.root = os.getcwd()
        self.abs_root_path_cache = {}
        self.fence = ("```", "```")
        self.warning_given = False

    def add_file(self, file_path):
        abs_path = self.abs_root_path(file_path)
        if os.path.isfile(abs_path):
            self.tracked_files.add(abs_path)
            self.check_added_files()
            self.io.tool_output(f"Added {file_path} to the chat.")
            return True
        else:
            if not os.path.exists(abs_path):
                if self.io.confirm_ask(f"Create new file {file_path}?"):
                    open(abs_path, "a").close()
                    self.tracked_files.add(abs_path)
                    self.check_added_files()
                    self.io.tool_output(f"Created and added {file_path}.")
                    return True
                else:
                    self.io.tool_warning(f"File {file_path} does not exist.")
                    return False
            else:
                self.io.tool_warning(f"File {file_path} is not a regular file.")
                return False

    def abs_root_path(self, path):
        key = path
        if key in self.abs_root_path_cache:
            return self.abs_root_path_cache[key]

        res = Path(self.root) / path
        res = res.resolve()
        self.abs_root_path_cache[key] = str(res)
        return str(res)

    def get_file_content(self, file_path):
        abs_path = self.abs_root_path(file_path)
        try:
            with open(abs_path, "r", encoding="utf-8") as file:
                return file.read()
        except IOError as e:
            self.io.tool_error(f"Error reading {file_path}: {e}")
            return None

    def get_tracked_files_content(self):
        content = ""
        for abs_path in self.tracked_files:
            rel_path = os.path.relpath(abs_path, self.root)
            file_content = self.get_file_content(rel_path)
            if file_content is not None and not is_image_file(abs_path):
                content += f"\n{rel_path}\n{self.fence[0]}\n"
                content += file_content
                content += f"{self.fence[1]}\n"
        return content

    def apply_edits(self, edits):
        for file_path, new_content in edits:
            abs_path = self.abs_root_path(file_path)
            try:
                with open(abs_path, "w", encoding="utf-8") as file:
                    file.write(new_content)
                self.io.tool_output(f"Applied edits to {file_path}")
            except IOError as e:
                self.io.tool_error(f"Error writing to {file_path}: {e}")

    def check_added_files(self):
        if self.warning_given:
            return

        warn_number_of_files = 4
        warn_number_of_tokens = 20 * 1024

        num_files = len(self.tracked_files)
        if num_files < warn_number_of_files:
            return

        tokens = 0
        for abs_path in self.tracked_files:
            if is_image_file(abs_path):
                continue
            content = self.get_file_content(abs_path)
            tokens += self.main_model.token_count(content)

        if tokens < warn_number_of_tokens:
            return

        self.io.tool_warning(
            "Warning: it's best to only add files that need changes to the chat."
        )
        self.warning_given = True
