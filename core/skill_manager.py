from skills.time_skill import TimeSkill
from skills.memory_skill import remember, recall


class SkillManager:

    def __init__(self):
        self.time_skill = TimeSkill()

    def execute(self, intent, command):

        if intent == "HELP":
            return '''
Available Commands:
help
time
remember <text>
recall
exit
'''

        elif intent == "EXIT":
            return "Goodbye."

        elif intent == "REMEMBER":

            text = command[len("remember "):]

            return remember(text)

        elif intent == "RECALL":

            return recall()

        response = self.time_skill.execute(intent)

        if response:
            return response

        return "Unknown command."
