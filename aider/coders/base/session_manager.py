# session_manager.py


class SessionManager:
    def __init__(self, main_model):
        self.conversation_history = []
        self.cur_messages = []
        self.main_model = main_model
        self.total_cost = 0.0
        self.message_cost = 0.0
        self.message_tokens_sent = 0
        self.message_tokens_received = 0

    def add_message(self, role, content):
        self.conversation_history.append({"role": role, "content": content})

    def get_formatted_history(self):
        return self.conversation_history + self.cur_messages

    def manage_tokens(self):
        # Implement token counting and management
        pass
