# code_manager.py

from aider.io import InputOutput


class Coder:
    def __init__(self, main_model, io=None):
        if io is None:
            io = InputOutput()
        self.io = io
        self.main_model = main_model
        self.file_manager = FileManager(io, main_model)
        self.session_manager = SessionManager(main_model)
        self.user_interface = UserInterface(io, self)
        self.version_control_manager = VersionControlManager(
            io, self.file_manager, main_model
        )
        self.llm_interface = LLMInterface(
            main_model, self.session_manager, self.user_interface, self.file_manager, io
        )
        self.auto_commits = True  # Assuming auto-commits are enabled
        self.dry_run = False

    def run(self):
        self.user_interface.display_output(f"Aider v{__version__}")
        self.user_interface.display_output("Welcome to the Code Assistant!")
        while True:
            user_message = self.user_interface.get_user_input("Your message: ")
            if user_message is None:
                continue
            if user_message.lower() in ["exit", "quit"]:
                break
            self.process_user_message(user_message)

    def process_user_message(self, user_message):
        # Handle commands
        command_result = self.user_interface.handle_command(user_message)
        if command_result is not None:
            return

        # Add user message to session
        self.session_manager.add_message("user", user_message)

        # Send message to LLM and process response
        response_generator = self.llm_interface.send_message(user_message)
        for _ in response_generator:
            pass  # Processed within LLMInterface

        # Apply edits if any
        edits = self.extract_edits_from_response()
        if edits:
            self.file_manager.apply_edits(edits)
            if self.auto_commits and not self.dry_run:
                files = [edit[0] for edit in edits]
                context = self.get_context_from_history()
                self.version_control_manager.commit_changes(
                    files, context, aider_edits=True
                )

    def extract_edits_from_response(self):
        # Implement logic to parse edits from LLM response
        # For example, parse the assistant's message for code blocks indicating edits
        return []

    def get_context_from_history(self):
        context = ""
        for msg in self.session_manager.cur_messages:
            context += f"{msg['role'].upper()}: {msg['content']}\n"
        return context
