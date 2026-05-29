class IntentRouter:

    def route(self, command):

        if command == "time":
            return "TIME"

        elif command == "help":
            return "HELP"

        elif command == "exit":
            return "EXIT"

        return "UNKNOWN"
