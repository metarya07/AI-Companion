import subprocess


class AppSkill:

    def open_app(self, app_name):

        if app_name == "notepad":
            subprocess.Popen("notepad.exe")
            return "Opening Notepad..."

        elif app_name == "calculator":
            subprocess.Popen("calc.exe")
            return "Opening Calculator..."

        elif app_name == "chrome":
            subprocess.Popen("chrome")
            return "Opening Chrome..."

        return "Application not supported."

    def execute(self, app_name):
        return self.open_app(app_name)
