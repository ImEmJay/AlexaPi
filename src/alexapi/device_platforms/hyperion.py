from __future__ import print_function

import json
import threading
import time
import websocket

import alexapi.bcolors as bcolors

from baseplatform import BasePlatform

class HyperionPlatform(BasePlatform):

	def __init__(self, config):
		if config['debug']:
			print("Initializing Hyperion platform")

		super(HyperionPlatform, self).__init__(config, 'hyperion')

		self.host = self._pconfig['hyperion_json_host']
		self.port = self._pconfig['hyperion_json_port']
		self.print_prefix = '{}[Hyperion]{}'.format(bcolors.BOLD, bcolors.ENDC)
		self.service = ''
		self.setup_complete = False
		self.socket = None
		self.socket_thread = None

	def setup(self):
		self.service = "ws://%s:%s" % (self.host, self.port)
		self.print_debug("Hyperion JSON Server - {}".format(self.service))
		self.init_connection()

	def after_setup(self):
		self.setup_complete = True
		self.check_connection()

	def check_connection(self):
		print('Checking Hyperion Connection')
		if self.socket_status():
			status = '{}OK{}'.format(bcolors.OKGREEN, bcolors.ENDC)
		else:
			status = '{}FAIL{}'.format(bcolors.FAIL, bcolors.ENDC)
		print('Connection {}'.format(status))

	def display_state(self, state):
		return 'start' if state else 'stop'

	def get_color(self, mode):
		return self._pconfig["color_{}".format(mode)]

	def handle_indicate(self, mode, state=False, flash=False):
		self.print_debug("indicate %s %s" % (mode, self.display_state(state)))
		flash = self.should_flash(mode)
		if not state and not flash:
			self.hyperion_clear()
		if state:
			self.hyperion_indicate(self.get_color(mode), flash)

	def hyperion_clear(self):
		if self._config['debug']:
			print("Clearing Hyperion settings")
		self.hyperion_send(self.hyperion_message('clear', True))

	def hyperion_effect(self, color, flash=False):
		effect = {'args': {'color': color}}
		if flash:
			effect['name'] = "Strobe white"
			effect['args']['frequency'] = self._pconfig['flash_frequency']
		else:
			effect['name'] = "Knight rider"
			effect['args']['speed'] = self._pconfig['hyperion_effect_speed']
		return {'effect': effect}

	def hyperion_indicate(self, color, flash=False, duration=False):
		command = self._pconfig['hyperion_mode']
		if flash and command == 'color':
			command = 'effect'
		if flash:
			duration = self._pconfig['flash_duration']
		options = self.hyperion_options(command, color, duration, flash)
		if self.setup_complete:
			self.hyperion_send(self.hyperion_message(command, True, options))

	def hyperion_options(self, command, color, duration=False, flash=False):
		options = {'color': color}
		if command == 'effect':
			options = self.hyperion_effect(color, flash)
		if duration:
			options['duration'] = duration
		return options

	def hyperion_message(self, command, priority=False, options=None):
		message = options or {}
		message['command'] = command
		if priority:
			message['priority'] = self._pconfig['hyperion_priority']
		return message

	def hyperion_send(self, message):
		if self._pconfig['verbose']:
			self.print_debug("sending '{}'".format(json.dumps(message)))
		if self.socket_status():
			self.socket.send(json.dumps(message))
		else:
			print("Unable to send Hyperion state update")
			self.init_connection()

	def indicate_failure(self):
		pass

	def indicate_playback(self, state=True):
		if self._pconfig['indicate_playback']:
			self.handle_indicate('playback', state)

	def indicate_processing(self, state=True):
		self.handle_indicate('processing', state)

	def indicate_recording(self, state=True):
		self.handle_indicate('recording', state)

	def indicate_success(self):
		pass

	def init_connection(self):
		self.print_debug('Initializing connection')
		if self._config['debug'] and self._pconfig['verbose']:
			websocket.enableTrace(True)
		self.socket = websocket.WebSocketApp(self.service,
				on_message=self.on_socket_message,
				on_close=self.on_socket_close,
				on_error=self.on_socket_error)
		self.socket_thread = threading.Thread(target=self.socket.run_forever)
		self.socket_thread.daemon = True
		self.socket_thread.start()

	def on_socket_close(self, ws): # pylint: disable=unused-argument
		self.print_debug('Closing connection')

	def on_socket_error(self, ws, error): # pylint: disable=unused-argument
		self.print_debug(error)

	def on_socket_message(self, ws, message): # pylint: disable=unused-argument
		message = json.loads(message)
		if not message['success']:
			self.print_error(message['error'])
		if self._pconfig['verbose']:
			self.print_debug("Received '{}'".format(message))

	def print_debug(self, message):
		if self._config['debug']:
			print(time.asctime(), self.print_prefix, message)

	def print_error(self, message):
		error_prefix = '{}Error{}:'.format(bcolors.FAIL, bcolors.ENDC)
		print(error_prefix, self.print_prefix, message)

	def should_flash(self, mode):
		return self._pconfig["flash_state_{}".format(mode)]

	def should_record(self):
		pass

	def socket_status(self):
		if not self.socket:
			return False
		return self.socket.sock and self.socket.sock.connected

	def cleanup(self):
		if self._config['debug']:
			print("Cleaning up Hyperion platform")
		self.hyperion_clear()
		if self.socket_status():
			self.socket.close()
