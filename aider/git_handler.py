# git_handler.py

import os
from pathlib import Path
from aider.repo import GitRepo, ANY_GIT_ERROR
from aider.init_utils import (
    setup_git,
    check_gitignore,
    guessed_wrong_repo,
    sanity_check_repo,
)
from aider.versioncheck import (
    check_version,
    install_from_main_branch,
    install_upgrade,
)

class GitHandler:
    def __init__(self, args, io, git_root, fnames, git_dname, main_model):
        self.args = args
        self.io = io
        self.git_root = git_root
        self.fnames = fnames
        self.git_dname = git_dname
        self.main_model = main_model
        self.repo = None

    def initialize_git(self):
        if self.args.git:
            self.git_root = setup_git(self.git_root, self.io)
            if self.args.gitignore:
                check_gitignore(self.git_root, self.io)

        if self.args.git:
            try:
                self.repo = GitRepo(
                    self.io,
                    self.fnames,
                    self.git_dname,
                    self.args.aiderignore,
                    models=self.main_model.commit_message_models(),
                    attribute_author=self.args.attribute_author,
                    attribute_committer=self.args.attribute_committer,
                    attribute_commit_message_author=self.args.attribute_commit_message_author,
                    attribute_commit_message_committer=self.args.attribute_commit_message_committer,
                    commit_prompt=self.args.commit_prompt,
                    subtree_only=self.args.subtree_only,
                )
            except FileNotFoundError:
                pass

        if not self.args.skip_sanity_check_repo:
            if not sanity_check_repo(self.repo, self.io):
                return 1

        return None
