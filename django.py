
from fabric.api import *
from virtualenv import *

def syncdb():
	""" syncs the django database """
	
	print(green("Syncing %s database" % env.project))
	
	with virtualenv():
		with cd(env.code_root):
			run('./manage.py syncdb --settings=%s.settings_%s' % (env.project,env.environment))
			
def runserver():
	""" runs the project as a development server """

	require('serverport',provided_by=development)

	print(green('Running development server.  Access at http://127.0.0.1:%s' % env.serverport))

	if env.environment == 'development':
		local('./manage.py runserver 0.0.0.0:%s --settings=%s.settings_%s' % (env.serverport,env.project,env.environment))
		return

	with virtualenv():
		with cd(env.code_root):
			run('./manage.py runserver 0.0.0.0:%s --settings=%s.settings_%s' % (env.serverport,env.project,env.environment))


def collectstatic():
	""" collects static files """

	print(green('Collecting static files'))

	with virtualenv():
		with cd(env.code_root):
			run('./manage.py collectstatic --settings=%s.settings_%s' % (env.project,env.environment))