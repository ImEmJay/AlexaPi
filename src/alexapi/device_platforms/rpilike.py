from __future__ import print_function
import time
from abc import ABCMeta

from baseplatform import BasePlatform
import alexapi.bcolors as bcolors

GPIO = None

class RPiLikePlatform(BasePlatform):
	__metaclass__ = ABCMeta

	def __init__(self, config, platform_name, p_GPIO):

		global GPIO
		GPIO = p_GPIO

		super(RPiLikePlatform, self).__init__(config, platform_name)

		self.button_pressed = False

	def setup(self):
		GPIO.setup(self._pconfig['button'], GPIO.IN, pull_up_down=GPIO.PUD_UP)
		GPIO.setup(self._pconfig['rec_light'], GPIO.OUT)
		GPIO.setup(self._pconfig['plb_light'], GPIO.OUT)
		GPIO.output(self._pconfig['rec_light'], GPIO.LOW)
		GPIO.output(self._pconfig['plb_light'], GPIO.LOW)

	def indicate_failure(self):
		for _ in range(0, 5):
			time.sleep(.1)
			GPIO.output(self._pconfig['rec_light'], GPIO.HIGH)
			time.sleep(.1)
			GPIO.output(self._pconfig['rec_light'], GPIO.LOW)

	def indicate_success(self):
		for _ in range(0, 5):
			time.sleep(.1)
			GPIO.output(self._pconfig['plb_light'], GPIO.HIGH)
			time.sleep(.1)
			GPIO.output(self._pconfig['plb_light'], GPIO.LOW)

	def after_setup(self, trigger_callback=None):

		self._trigger_callback = trigger_callback

		# threaded detection of button press
		GPIO.add_event_detect(self._pconfig['button'], GPIO.FALLING, callback=self.detect_button, bouncetime=100)

	def indicate_recording(self, state=True):
		GPIO.output(self._pconfig['rec_light'], GPIO.HIGH if state else GPIO.LOW)

	def indicate_playback(self, state=True):
		GPIO.output(self._pconfig['plb_light'], GPIO.HIGH if state else GPIO.LOW)

	def indicate_processing(self, state=True):
		GPIO.output(self._pconfig['plb_light'], GPIO.HIGH if state else GPIO.LOW)
		GPIO.output(self._pconfig['rec_light'], GPIO.HIGH if state else GPIO.LOW)

	def detect_button(self, channel=None): # pylint: disable=unused-argument
		self.button_pressed = True

		if self._trigger_callback:
			self._trigger_callback(self.force_recording)

		if self._config['debug']:
			print("{}Button pressed!{}".format(bcolors.OKBLUE, bcolors.ENDC))

		time.sleep(.5)  # time for the button input to settle down
		while GPIO.input(self._pconfig['button']) == 0:
			time.sleep(.1)

		if self._config['debug']:
			print("{}Button released.{}".format(bcolors.OKBLUE, bcolors.ENDC))

		self.button_pressed = False

		time.sleep(.5)  # more time for the button to settle down

	# def wait_for_trigger(self):
	# 	# we wait for the button to be pressed
	# 	GPIO.wait_for_edge(self._pconfig['button'], GPIO.FALLING)

	def force_recording(self):
		return self.button_pressed

	def cleanup(self):
		GPIO.remove_event_detect(self._pconfig['button'])

		GPIO.output(self._pconfig['rec_light'], GPIO.LOW)
		GPIO.output(self._pconfig['plb_light'], GPIO.LOW)
