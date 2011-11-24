from fabric.api import *
from contextlib import contextmanager as _contextmanager
from fabric.colors import *
import os

@_contextmanager
def virtualenv():
	""" Wrapper function to ensure code is run under a virtual environment """
	
	venv_dir=os.path.join(env.virtualenv_root, env.project)
	activate='source ' + os.path.join(venv_dir,'bin','activate')

	with prefix(activate):
	    yield