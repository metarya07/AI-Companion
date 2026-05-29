from skills.time_skill import TimeSkill


class SkillManager:

    def __init__(self):
        self.time_skill = TimeSkill()

    def execute(self, intent):

        if intent == "HELP":
            return '''
Available Commands:
help
time
exit
'''

        elif intent == "EXIT":
            return "Goodbye."

        response = self.time_skill.execute(intent)

        if response:
            return response

        return "Unknown command."
