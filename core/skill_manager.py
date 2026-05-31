from skills.time_skill import TimeSkill
from skills.system_skill import SystemSkill
from skills.app_skill import AppSkill
from skills.memory_skill import remember, recall, forget


class SkillManager:

    def __init__(self):
        self.time_skill = TimeSkill()
        self.system_skill = SystemSkill()
        self.app_skill = AppSkill()

    def execute(self, intent, command):

        if intent == "HELP":
            return '''
Available Commands:
help
time
cpu
ram
status
open <app>
remember <text>
forget <id>
recall
exit
'''

        elif intent == "EXIT":
            return "Goodbye."

        elif intent == "REMEMBER":

            text = command[len("remember "):]

            return remember(text)

        elif intent == "FORGET":

            memory_text = command[len("forget "):].strip()

            if not memory_text.isdigit():
                return "Please provide a valid memory ID."

            memory_id = int(memory_text)

            return forget(memory_id)

        elif intent == "OPEN_APP":

            app_name = command[len("open "):].strip().lower()

            return self.app_skill.execute(app_name)

        elif intent == "RECALL":

            return recall()

        response = self.system_skill.execute(intent)

        if response:
            return response

        response = self.time_skill.execute(intent)

        if response:
            return response

        return "Unknown command."
