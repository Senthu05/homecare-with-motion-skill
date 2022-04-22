import time
import datetime
import RPi.GPIO as GPIO
import re

from mycroft import MycroftSkill, intent_file_handler
from datetime import datetime, timedelta
from mycroft.util.time import now_utc, to_local, now_local

sensor_pin = [19, 20, 21, 22, 23, 24]  # define the sensor pins
MOTION = 17  # GPIO pins for motion sensor
LED = 25  # LED output
record_dic = {}  # record the motion
sensor_room = ["living"]  # room name need to be assigned from the site
bed_time = "210000"
wake_time = "060000"
first_check_time = 60.0  # how frequently check the motion
second_check_time = 40.0  # how long wait after no respond for first check
no_respond_flag = True


class HomecareWithMotion(MycroftSkill):
    def __init__(self):
        MycroftSkill.__init__(self)

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
                                          None, 10, 'check_motion')
            record_dic["time loaded"] = now_local()

    def handle_motion(self, message):
        for x in range(len(sensor_room)):  # check all sensors
            if GPIO.event_detected(sensor_pin[x]):
                self.log.info("event detected")
                event_time = now_local()
                record_dic["time loc" + str(x)] = event_time
                self.cancel_scheduled_event('no_respond')
        # time_list = [k for k in record_dic.values()]  # all, time values as

        # get all the values which match the key start with "time" used regex pattern match
        time_list = [v for k, v in record_dic.items() if bool(re.match("time", k))]

        now = now_local()
        # gap = now - (time_list[0] if len(time_list) >= 1 else now)  # random value
        gap = timedelta(seconds=first_check_time + 1.0)
        for y in range(len(time_list)):
            temp_gap = now - time_list[y]
            if temp_gap <= gap:
                gap = temp_gap

        gap_second = gap.total_seconds()  # convert the gap in second
        bed_timeHour = datetime.strptime(bed_time, "%H%M%S").time()
        wake_timeHour = datetime.strptime(wake_time, "%H%M%S").time()
        current_hour = now.time()

        # check both condition 1 hour gap and bedtime
        if gap_second > first_check_time and (wake_timeHour < current_hour < bed_timeHour):
            self.log.info(time_list)
            time_list.clear()
            record_dic.clear()  # clear the dictionary
            record_dic["time interaction"] = now_local()  # record the time (must, to check the different)
            confirm = self.ask_yesno("motion.confirmation")
            self.verify_yesno(confirm)

    def is_None_handler(self):
        confirm = self.ask_yesno("no.Respond.confirmation")
        if confirm == "yes":
            record_dic["confirmation time for 2nd attempt"] = now_local()
        self.verify_yesno(confirm)

    def verify_yesno(self, confirm):
        self.log.info("I am here in verify_yesno function")
        if confirm == "yes":
            self.speak_dialog("no.help.confirmation")
        elif confirm == "no":
            # need to ask question about the email body
            title = "Immediate help needed"
            body = "I have been asked for a help. Can you please check ?"
            self.send_email(title, body)
            self.speak("I have just sent a email")
        elif confirm is None:
            global no_respond_flag
            if no_respond_flag:
                self.schedule_event(self.is_None_handler, None, second_check_time, None, 'no_respond')
                no_respond_flag = not no_respond_flag
                record_dic["No respond"] = now_local()
            else:
                # this else part will run on the second check
                title = "Immediate help needed"
                body = "I don't get any respond, Could you please check it?"
                self.send_email(title, body)
                record_dic["again no respond"] = now_local()
        else:
            confuse = self.ask_yesno("again.confirm.motion") # do you need help?
            if confuse == "no":
                self.speak_dialog("no.help.confirmation")
                # need to ask question about the email body
            elif confuse == "yes":
                title = "Immediate help needed"
                body = "I have been asked for a help. Can you please check ?"
                self.send_email(title, body)
                self.speak("I have just sent a email")
            else:
                title = "Alert from Mycroft skill"
                body = "I am having trouble to communicate with, Can you please check ?"
                self.send_email(title, body)
                self.speak("email has been sent")

    @intent_file_handler('motion.with.homecare.intent')
    def handle_motion_with_homecare(self, message):
        self.speak_dialog('motion.with.homecare')


def create_skill():
    return HomecareWithMotion()
