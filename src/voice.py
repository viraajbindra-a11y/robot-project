class Voice:
    def __init__(self):
        self.last_command = None

    def speak(self, message):
        # Minimal implementation for tests and offline development.
        return f"Speaking: {message}"

    def listen(self, command=None):
        # If command provided, set last_command (used by tests). In a real
        # implementation this would record audio and do speech-to-text.
        if command is not None:
            self.last_command = command
            return command
        # No-op for now
        return None