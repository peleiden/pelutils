import os
import traceback as tb
import copy
from functools import wraps, update_wrapper
from itertools import chain
from typing import Callable, List

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

	fpath: str
	_default_sep: str
	_include_micros: bool
	_verbose: bool

	def __init__(self):
		self._is_configured = False
		self._unverbose = _Unverbose()
		self._collect = False
		self._collected_log: List[str] = list()
		self._collected_print: List[str] = list()

	def configure(self, fpath: str, title: str, default_seperator="\n", include_micros=False, verbose=True):
		if self._is_configured:
			raise LoggingException("Logger has already been configured. Use log.clean to reset logger")

		dirs = os.path.join(*os.path.split(fpath)[:-1])
		if dirs:
			os.makedirs(dirs, exist_ok=True)

		self.fpath = fpath
		self._default_sep = default_seperator
		self._include_micros = include_micros
		self._verbose = verbose

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

	def _write_to_log(self, content: str):
		with open(self.fpath, "a", encoding="utf-8") as logfile:
			logfile.write(content + "\n")

	def _log(self, *tolog, with_timestamp=True, sep=None, with_print=True):
		if not self._is_configured:
			return

		sep = sep or self._default_sep
		time = get_timestamp()
		tolog = sep.join([str(x) for x in tolog])
		spaces = len(time) * " "
		space = " " * 5
		logs = tolog.split("\n")
		if with_timestamp and tolog:
			logs[0] = f"{time}{space}{logs[0]}"
		else:
			logs[0] = f"{spaces}{space}{logs[0]}"
		for i in range(1, len(logs)):
			logs[i] = f"{spaces}{space}{logs[i]}"
			if logs[i].strip() == "":
				logs[i] = ""
		tolog = "\n".join(x.rstrip() for x in logs)
		if not self._collect:
			self._write_to_log(tolog)
			if with_print:
				print(tolog)
		else:
			self._collected_log.append(tolog)
			if with_print:
				self._collected_print.append(tolog)

	def verbose(self, *tolog, with_timestamp=True, sep=None, with_print=True):
		if self._verbose and self.unverbose.allow_verbose:
			self._log(*tolog, with_timestamp=with_timestamp, sep=sep, with_print=with_print)

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

	def _reset_collected(self):
		self._collected_log = list()
		self._collected_print = list()

	def set_collect_mode(self, collect: bool):
		self._collect = collect
		if not collect:
			self._reset_collected()

	def log_collected(self):
		if self._collected_log:
			self._write_to_log("\n".join(self._collected_log))
		if self._collected_print:
			print("\n".join(self._collected_print))


log = Logger()


class collect_logs:
	""" Wrap functions with this class to have them output all their output at once. Useful with multiprocessing """
	def __init__(self, fun: Callable):
		self.fun = fun
		update_wrapper(self, fun)

	def __call__(self, *args, **kwargs):
		log.set_collect_mode(True)
		return_value = self.fun(*args, **kwargs)
		log.log_collected()
		log.set_collect_mode(False)
		return return_value
