from core.command_parser import CommandParser
from core.intent_router import IntentRouter
from core.skill_manager import SkillManager


class Brain:

    def __init__(self):

        self.parser = CommandParser()
        self.router = IntentRouter()
        self.skills = SkillManager()

    def process(self, user_input):

        command = self.parser.parse(user_input)

        intent = self.router.route(command)

        return self.skills.execute(intent, command)
