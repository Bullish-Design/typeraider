# user_interface.py

from aider.commands import Commands


class UserInterface:
    def __init__(self, io, coder):
        self.io = io
        self.commands = Commands(io, coder)

    def get_user_input(self, prompt):
        return self.io.get_input(prompt)

    def display_output(self, message):
        self.io.tool_output(message)

    def confirm_action(self, prompt, subject=None):
        return self.io.confirm_ask(prompt, subject=subject)

    def handle_command(self, command):
        if self.commands.is_command(command):
            return self.commands.run(command)
        else:
            return None
