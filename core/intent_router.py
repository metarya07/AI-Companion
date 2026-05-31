class IntentRouter:

    def route(self, command):

        command_lower = command.lower()

        if command_lower.startswith("remember "):
            return "REMEMBER"

        elif command_lower.startswith("forget "):
            return "FORGET"

        elif command_lower == "recall":
            return "RECALL"

        elif command_lower == "time":
            return "TIME"

        elif command_lower == "help":
            return "HELP"

        elif command_lower == "exit":
            return "EXIT"

        return "UNKNOWN"
