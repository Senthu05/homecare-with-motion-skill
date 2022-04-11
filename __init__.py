import time
import datetime
import RPi.GPIO as GPIO

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
                                          None, 0.1, 'check_motion')

    def handle_motion(self, message):
        for x in range(len(sensor_room)):  # check all sensors
            if GPIO.event_detected(sensor_pin[x]):
                event_time = now_local()
                record_dic["loc" + str(x)] = event_time
        time_list = [k for k in record_dic.values()]  # all time values as list

        now = now_local()
        gap = now - (time_list[0] if len(time_list) >= 1 else now)  # random value
        for y in range(len(time_list)):
            temp_gap = now_local() - time_list[y]
            if temp_gap <= gap:
                gap = temp_gap

        bed_timeHour = datetime.strptime(bed_time, "%H%M%S").time()
        wake_timeHour = datetime.strptime(wake_time, "%H%M%S").time()
        current_hour = now.time()
        # current_hour = datetime.now_local().time()

        # check both condition 1 hour gap and bedtime
        if gap.total_second() > 3600 and (wake_timeHour < current_hour < bed_timeHour):
            self.speak_dialog("confirm.motion")

    @intent_file_handler('motion.with.homecare.intent')
    def handle_motion_with_homecare(self, message):
        self.speak_dialog('motion.with.homecare')


def create_skill():
    return HomecareWithMotion()
