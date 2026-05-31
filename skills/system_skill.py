import psutil


class SystemSkill:

    def get_cpu_usage(self):
        cpu = psutil.cpu_percent(interval=1)
        return f"CPU Usage: {cpu}%"

    def get_ram_usage(self):
        ram = psutil.virtual_memory().percent
        return f"RAM Usage: {ram}%"

    def get_status(self):
        cpu = psutil.cpu_percent(interval=1)
        ram = psutil.virtual_memory().percent

        return (
            f"CPU Usage: {cpu}%\n"
            f"RAM Usage: {ram}%"
        )

    def execute(self, intent):

        if intent == "CPU":
            return self.get_cpu_usage()

        elif intent == "RAM":
            return self.get_ram_usage()

        elif intent == "STATUS":
            return self.get_status()

        return None
