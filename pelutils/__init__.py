import numpy as np
import random
from datetime import datetime

try:
	import git
	has_git = True
except ModuleNotFoundError:
	has_git = False

try:
	import torch
	has_torch = True
except ModuleNotFoundError:
	has_torch = False

def seedsetter():
	if has_torch:
		torch.manual_seed(0)
		torch.cuda.manual_seed(0)
		torch.cuda.manual_seed_all(0)
		torch.backends.cudnn.deterministic = True
		torch.backends.cudnn.benchmark = False
	np.random.seed(0)
	random.seed(0)


def get_commit() -> str:
	if has_git:
		repo = git.Repo(".")  # TODO: Search upwards in directories
		return str(repo.head.commit)
	return "Unknown (install GitPython to get this)"



def get_timestamp(for_file: bool=False) -> str:
	"""
	Returns a time stamp

	:param for_file: File friendly format, if True
	:param type param:  Argument
	"""
	d_string = str(datatime.now())
	if for_file: d_string = "-".join(d_string.split(".")[0].split(":")).replace(" ", "_")
	return d_string


# To allow imports directly from utils #
# Currently to be placed lower because get_timestamp is needed by logger #
from .logger import *
from .parse import *
from .ticktock import *
