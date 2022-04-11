from mycroft import MycroftSkill, intent_file_handler

class HomecareWithMotion(MycroftSkill):
    def __init__(self):
        MycroftSkill.__init__(self)

    @intent_file_handler('motion.with.homecare.intent')
    def handle_motion_with_homecare(self, message):
        self.speak_dialog('motion.with.homecare')

def create_skill():
    return HomecareWithMotion()
-
