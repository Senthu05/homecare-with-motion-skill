import time
import datetime
import RPi.GPIO as GPIO
import re

from mycroft import MycroftSkill, intent_file_handler
from datetime import datetime, timedelta
from mycroft.util.time import now_utc, to_local, now_local
from mycroft.util.format import join_list

sensor_pin = [19, 20, 21, 22, 23, 24]  # define the sensor pins
MOTION = 17  # GPIO pins for motion sensor
LED = 25  # LED output
record_dic = {}  # record the motion
sensor_room = ["living"]  # room name need to be assigned from the site
bed_time = "210000"
wake_time = "060000"
first_check_time = timedelta(seconds=60)  # how frequently check the motion
second_check_time = 20.0  # how long wait after no respond for first check
no_respond_flag = True


class HomecareWithMotion(MycroftSkill):
    def __init__(self):
        MycroftSkill.__init__(self)
        self.immediate_help = ["slipped", "fell down", "hurt", "bleeding", "hit"]
        self.ask_to_inform = ["can not walk", "can't walk", "can not wake up", "cannot wake up"]
        self.medicine = ["headache", "fever", "stomach"]
        self.inform = ["call", "inform", "email", "ring"]
        self.more_question = ["i don't know", "I have no idea"]
        self.make_fun = ["lazy", "lonely"]
        self.angry = ["shut your mouth", "shut up", "stop"]

    def initialize(self):
        my_setting = self.settings.get('my_setting')
        # show_time = self.settings.get('show_time', False)
        try:
            GPIO.setmode(GPIO.BCM)
            GPIO.setwarnings(False)
            GPIO.setup(LED, GPIO.OUT)
            for x in range(len(sensor_room)):  # loop run for every room
                GPIO.setup(sensor_pin[x], GPIO.IN, pull_up_down=GPIO.PUD_DOWN)  # enable the pull-up
                GPIO.remove_event_detect(sensor_pin[x])
                GPIO.add_event_detect(sensor_pin[x], GPIO.RISING,
                                      bouncetime=500)  # high bounce time to avoid the event frequently detection

        except:
            self.log.warning("Can't initialize GPIO - skill will not load")
            self.speak_dialog("error.initialize")  # create the error.initialise.dialog file

        finally:
            self.schedule_repeating_event(self.handle_motion,
                                          None, 20, name='check_motion')
            record_dic["time loaded"] = now_local()

    def handle_motion(self, message):
        global record_dic
        for x in range(len(sensor_room)):  # check all sensors
            if GPIO.event_detected(sensor_pin[x]):
                self.log.info("event detected")
                event_time = now_local()
                record_dic["time loc" + str(x)] = event_time
                self.cancel_scheduled_event('no_respond')
        # get all the values which match the key start with "time" used regex pattern match
        time_list = [v for k, v in record_dic.items() if bool(re.match("time", k))]
        now = now_local()
        gap = timedelta(seconds=0)  # random value
        for y in range(len(time_list)):
            temp_gap = now - time_list[y]
            if temp_gap > gap:
                gap = temp_gap
        gap_second = gap.total_seconds()  # convert the gap in second
        bed_timeHour = datetime.strptime(bed_time, "%H%M%S").time()
        wake_timeHour = datetime.strptime(wake_time, "%H%M%S").time()
        current_hour = now.time()
        if gap_second > first_check_time.total_seconds() and (wake_timeHour < current_hour < bed_timeHour):
            self.log.info(time_list)
            record_dic.clear()  # clear the dictionary
            record_dic["time interaction"] = now_local()  # record the time (must, to check the different)
            self.conversation()

    @intent_file_handler('motion.with.homecare.intent')
    def handle_motion_with_homecare(self, message):
        title = "no help needed"
        self.mail(title, message)
        self.speak_dialog('motion.with.homecare')

    def conversation(self):
        resp = self.get_response("motion.confirmation")
        if self.voc_match(resp, 'yes'):
            self.speak_dialog("no.help.confirmation")
        elif self.voc_match(resp, 'no'):
            no_resp = self.get_response("how.can.i.help")
            self.help(no_resp)
        elif resp is not None:
            self.help(resp)
        else:
            global no_respond_flag
            no_respond_flag = not no_respond_flag
            if no_respond_flag:
                title = "no respond"
                body = "Hi,\nI couldn't reach the resident after 2 attempt"
                self.send_email(title, body)
            else:
                self.schedule_event(self.conversation, second_check_time, name="no_respond")

    def mail(self, title, utterance):
        body = "Hi,\n This is the respond I received" + utterance
        self.send_email(title, body)

    def help(self, response):
        immediate_help_words = [a for a in self.immediate_help if a in response]
        ask_to_inform_words = [a for a in self.ask_to_inform if a in response]
        medicine_words = [a for a in self.medicine if a in response]
        inform_words = [a for a in self.inform if a in response]
        more_question_words = [a for a in self.more_question if a in response]
        make_fun_words = [a for a in self.make_fun if a in response]
        angry_words = [a for a in self.angry if a in response]

        if len(immediate_help_words) > 0:
            self.speak_dialog("immediate.help", data={'immediate': join_list(immediate_help_words, "and")})
            title = "immediate help"
            self.mail(title, response)
        elif len(ask_to_inform_words) > 0:
            yes_no = self.ask_yesno("ask.to.inform", data={'ask': join_list(ask_to_inform_words, "and")})
            if yes_no == "yes":
                title = ask_to_inform_words[0]
                self.mail(title, response)
        elif len(medicine_words) > 0:
            title = medicine_words[0]
            yes_no = self.ask_yesno("medicine", data={})
            if yes_no == "no":
                title = "Did not get medicine"
                self.speak("You better get medicine now")
            elif yes_no == "yes":
                self.speak("good to hear that you got medicine")
                title = medicine_words[0]
            self.mail(title, response)
        elif len(inform_words) > 0:
            resp = self.get_response("inform")
            title = "need to contact"
            self.mail(title, resp)
            self.speak("Ok informing")
        elif len(more_question_words) > 0:
            self.schedule_event(self.more_question_handler, 1.0, name="more_question")
        elif len(make_fun_words) > 0:
            self.speak_dialog("make.fun", data={'fun': join_list(immediate_help_words, "or")})
        elif len(angry_words) > 0:
            self.speak_dialog("angry")
        else:
            self.speak_dialog("else.help")
            title = "confuse conversation"
            self.mail(title, response)

    def more_question_handler(self):
        resp = self.get_response("more.question")
        self.help(resp)


def create_skill():
    return HomecareWithMotion()
