import random
from datetime import datetime

import numpy as np
import torch

try:
	import git
	has_git = True
except ModuleNotFoundError:
	has_git = False

def set_seeds(seed: int = 0) -> int:
	torch.manual_seed(seed)
	torch.cuda.manual_seed(seed)
	torch.cuda.manual_seed_all(seed)
	torch.backends.cudnn.deterministic = True
	torch.backends.cudnn.benchmark = False
	np.random.seed(seed)
	random.seed(seed)
	return seed

def get_commit() -> str:
	if has_git:
		repo = git.Repo(".")  # TODO: Search upwards in directories
		return str(repo.head.commit)
	return "Unknown (install GitPython to get this)"

def get_timestamp(for_file: bool = False) -> str:
	"""
	Returns a time stamp for current time either in datetime format or, if for_file, in YYYY-MM-DD_HH-MM-SS
	"""
	d_string = str(datetime.now())
	if for_file: d_string = "-".join(d_string.split(".")[0].split(":")).replace(" ", "_")
	return d_string

# To allow imports directly from utils #
# Currently to be placed lower because get_timestamp is needed by logger #
from .logger import *
from .parse import *
from .ticktock import *
from .datahandling import *
