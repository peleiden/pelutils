import os

from . import get_timestamp

class Unverbose:
	"""
	Used for disabling verbose logging in a code section
	Example:
	log = Logger(..., verbose=True)
	with unverbose:
		log("This will be logged")
		log.verbose("This will not be logged")
	"""
	allow_verbose = True

	def __enter__(self):
		self.allow_verbose = False

	def __exit__(self, *args):
		self.allow_verbose = True

unverbose = Unverbose()


class Logger:
	"""
	A simple logger which creates a log file and pushes strings both to stdout and the log file
	Sections, verbosity and error logging is supported
	"""
	_default_sep = "\n"

	def __init__(self, fpath: str, title: str, verbose=True):
		dirs = "/".join(fpath.split('/')[:-1])
		if not os.path.exists(dirs) and dirs:
			os.makedirs(dirs)

		self.fpath = fpath
		self._verbose = verbose

		with open(self.fpath, "w+", encoding="utf-8") as logfile:
			logfile.write("")

		self.log(title + "\n")

	def __call__(self, *tolog, with_timestamp=True, sep=None):
		self.log(*tolog, with_timestamp=with_timestamp, sep=sep)

	def log(self, *tolog, with_timestamp=True, sep=None):
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
			print(tolog)

	def verbose(self, *tolog, with_timestamp=True):
		if self._verbose and unverbose.allow_verbose:
			self(*tolog, with_timestamp=with_timestamp)

	def is_verbose(self):
		return self._verbose and unverbose.allow_verbose

	def section(self, title=""):
		self.log()
		self.log(title)

	def throw(self, error: Exception, with_timestamp=True):
		self.log(error, with_timestamp=with_timestamp)
		raise error


class NullLogger(Logger):
	_verbose = False
	def __init__(self, *args, **kwargs):
		pass
	def log(self, *tolog, **kwargs):
		pass
	def section(self, title=""):
		pass
