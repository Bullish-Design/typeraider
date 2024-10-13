# version_control_manager.py

from aider.repo import GitRepo, ANY_GIT_ERROR


class VersionControlManager:
    def __init__(self, io, file_manager, main_model):
        self.io = io
        self.file_manager = file_manager
        self.main_model = main_model
        self.repo = None
        try:
            self.repo = GitRepo(
                io,
                list(file_manager.tracked_files),
                None,
                models=main_model.commit_message_models(),
            )
        except FileNotFoundError:
            self.io.tool_warning("No Git repository found.")

    def commit_changes(self, files, context, aider_edits=False):
        if not self.repo:
            self.io.tool_warning("No repository to commit changes.")
            return False
        try:
            res = self.repo.commit(
                fnames=files, context=context, aider_edits=aider_edits
            )
            if res:
                commit_hash, commit_message = res
                self.io.tool_output(f"Changes committed: {commit_hash}")
                return True
            return False
        except ANY_GIT_ERROR as err:
            self.io.tool_error(f"Error during commit: {err}")
            return False

    def undo_last_commit(self):
        if not self.repo:
            self.io.tool_warning("No repository to undo changes.")
            return False
        try:
            self.repo.undo_last_commit()
            self.io.tool_output("Last commit undone.")
            return True
        except ANY_GIT_ERROR as err:
            self.io.tool_error(f"Error during undo: {err}")
            return False

    def check_repo_status(self):
        if not self.repo:
            return None
        return self.repo.status()
