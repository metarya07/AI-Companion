from datetime import datetime


class TimeSkill:

    def execute(self, intent):

        if intent == "TIME":
            return f"Current Time: {datetime.now().strftime('%H:%M:%S')}"

        return None
