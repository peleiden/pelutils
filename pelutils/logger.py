import os
import traceback as tb
from itertools import chain

from pelutils import get_timestamp


class _Unverbose:
	"""
	Used for disabling verbose logging in a code section
	Example:
	with log.unverbose:
		log("This will be logged")
		log.verbose("This will not be logged")
	"""
	allow_verbose = True

	def __enter__(self):
		self.allow_verbose = False

	def __exit__(self, *args):
		self.allow_verbose = True


class LoggingException(Exception):
	pass


class Logger:
	"""
	A simple logger which creates a log file and pushes strings both to stdout and the log file
	Sections, verbosity and error logging is supported
	"""

	_unverbose = _Unverbose()
	_default_sep: str
	_include_micros: bool
	_is_configured = False

	def configure(self, fpath: str, title: str, default_seperator="\n", include_micros=False):
		if self._is_configured:
			raise LoggingException("Logger has already been configured. Use log.clean to reset logger")

		dirs = "/".join(fpath.split('/')[:-1])
		if not os.path.exists(dirs) and dirs:
			os.makedirs(dirs)

		self.fpath = fpath
		self._default_sep = default_seperator
		self._include_micros = include_micros

		with open(self.fpath, "w", encoding="utf-8") as logfile:
			logfile.write("")

		self._is_configured = True
		self._log(title + "\n")

	def clean(self):
		if not self._is_configured:
			raise LoggingException("Logger is not configured and thus cannot be cleaned")

		del self._default_sep
		del self._include_micros
		del self.fpath
		self._is_configured = False

	@property
	def unverbose(self):
		return self._unverbose

	def __call__(self, *tolog, with_timestamp=True, sep=None):
		self._log(*tolog, with_timestamp=with_timestamp, sep=sep)

	def _log(self, *tolog, with_timestamp=True, sep=None, with_print=True):
		if not self._is_configured:
			raise LoggingException("Logger has not been configured")

		sep = sep or self._default_sep
		time = get_timestamp()
		with open(self.fpath, "a", encoding="utf-8") as logfile:
			tolog = sep.join([str(x) for x in tolog])
			spaces = len(time) * " "
			logs = tolog.split("\n")
			if with_timestamp and tolog:
				logs[0] = f"{time}\t{logs[0]}"
			else:
				logs[0] = f"{spaces}\t{logs[0]}"
			for i in range(1, len(logs)):
				logs[i] = f"{spaces}\t{logs[i]}"
				if logs[i].strip() == "":
					logs[i] = ""
			tolog = "\n".join(x.rstrip() for x in logs)
			logfile.write(tolog+"\n")
			if with_print:
				print(tolog)

	def verbose(self, *tolog, with_timestamp=True):
		if self.unverbose.allow_verbose:
			self._log(*tolog, with_timestamp=with_timestamp)

	def section(self, title=""):
		self._log()
		self._log(title)

	def throw(self, error: Exception):
		try:
			raise error
		except:
			self._log("ERROR: %s thrown with stacktrace" % type(error).__name__)
			# Get stack except the part thrown here
			stack = tb.format_stack()[:-1]
			# Format the stacktrace such that empty lines are removed
			stack = list(chain.from_iterable([elem.split("\n") for elem in stack]))
			stack = [line for line in stack if line.strip()]
			self._log(*stack, with_timestamp=False, with_print=False)
		raise error

	def input(self, prompt=""):
		self._log("Waiting for user input")
		self._log("Prompt: %s" % prompt, with_print=False)
		response = input(prompt)
		self._log("Input:  %s" % response, with_print=False)
		return response


log = Logger()
