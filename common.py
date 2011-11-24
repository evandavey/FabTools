from fabric.api import *
from fabric.colors import *
from contextlib import contextmanager as _contextmanager
import os

"""
Commands - setup
"""
def setup():
    """
    Setup a fresh virtualenv, install everything we need, and fire up the database.
    
    Does NOT perform the functions of deploy().
    """

    if env.environment != 'development':
    
        setup_directories()
        setup_virtualenv()
        clone_repo()
        checkout_latest()
        destroy_database()
        create_database()
        load_data()
        install_requirements()
        install_apache_conf()
   
def setup_directories():
    """
    Create directories necessary for deployment.
    """
    print(green("Creating project directories"))
    run('mkdir -p %(root)s' % env)
    run('mkdir -p %s' % os.path.join(env.home, 'www', 'log'))


def setup_virtualenv():
	""" creates a virtual environment """

	print(green("Creating a virtual environment in %s" % env.virtualenv_root))
	sudo('WORKON_HOME=%s' % (env.virtualenv_root) + ' && ' + 'source /usr/local/bin/virtualenvwrapper.sh && ' + 'mkvirtualenv --no-site-packages %s' % (env.project),user=env.user)


def clone_repo():
    """
    Do initial clone of the git repository.
    """
    run('git clone %(repo)s %(code_root)s' % env)

def checkout_latest():
    """
    Pull the latest code on the specified branch.
    """
    
    run('cd %(code_root)s; git checkout %(branch)s; git pull origin %(branch)s' % env)


def install_requirements():
    """ update external dependencies using pip """

    print(green("Installing dependencies - this may take some time, please be patient"))
    requirements = os.path.join(env.code_root, 'requirements')
    requirements_file=get(os.path.join(requirements, '%s.txt' % env.environment))[0]

    with virtualenv():
        ## hack to overcome no order in requirements files	
        for line in open(requirements_file, "r"): 
            run("pip install %s" % (line))


def install_apache_conf():
    """
    Install the apache site config file.
    """
    #sudo('cp %(repo_path)s/%(project_name)s/configs/%(settings)s/%(project_name)s %(apache_config_path)s' % env)


"""
Commands - deployment
"""
def deploy():
    """
    Deploy the latest version of the site to the server and restart Apache2.
    
    Does not perform the functions of load_new_data().
    """
    require('settings', provided_by=[production, staging])
    require('branch', provided_by=[stable, master, branch])
    
    with settings(warn_only=True):
        maintenance_up()
        
    checkout_latest()
    gzip_assets()
    maintenance_down()
    
def maintenance_up():
    """
    Install the Apache maintenance configuration.
    """
    sudo('cp %(repo_path)s/%(project_name)s/configs/%(settings)s/%(project_name)s_maintenance %(apache_config_path)s' % env)
    reboot()

def gzip_assets():
    """
    GZips every file in the assets directory and places the new file
    in the gzip directory with the same filename.
    """
    run('cd %(repo_path)s; python gzip_assets.py' % env)


def reboot(): 
    """
    Restart the Apache2 server.
    """
    #sudo('/mnt/apps/bin/restart-all-apache.sh')
    
def maintenance_down():
    """
    Reinstall the normal site configuration.
    """
    install_apache_conf()
    reboot()
    
"""
Commands - rollback
"""
def rollback(commit_id):
    """
    Rolls back to specified git commit hash or tag.
    
    There is NO guarantee we have committed a valid dataset for an arbitrary
    commit hash.
    """
    require('settings', provided_by=[production, staging])
    require('branch', provided_by=[stable, master, branch])
    
    maintenance_up()
    checkout_latest()
    git_reset(commit_id)
    gzip_assets()
    deploy_to_s3()
    refresh_widgets()
    maintenance_down()
    
def git_reset(commit_id):
    """
    Reset the git repository to an arbitrary commit hash or tag.
    """
    env.commit_id = commit_id
    run("cd %(repo_path)s; git reset --hard %(commit_id)s" % env)

"""
Commands - data
"""
def load_new_data():
    """
    Erase the current database and load new data from the SQL dump file.
    """
    
    maintenance_up()
    destroy_database()
    create_database()
    load_data()
    maintenance_down()
    
def create_database():
    """
    Creates the user and database for this project.
    """
    
    user_sql="grant all privileges on %(db)s.* to '%(db_user)s'@'%%'identified by '%(db_password)s" % env
    
   
    run('echo "create database %(db)s" | mysql -uroot -p'  % env)
    run('echo "%s" | mysql -uroot -p'  % user_sql)
    
def destroy_database():
    """
    Destroys the user and database for this project.
    
    Will not cause the fab to fail if they do not exist.
    """
    with settings(warn_only=True):
        run('echo "drop database if exists %(db)s" | mysql -uroot -p'  % env)
       
        
def load_data():
    """
    Loads data from the repository into PostgreSQL.
    """
    #run('psql -q %(project_name)s < %(path)s/repository/data/psql/dump.sql' % env)
    #run('psql -q %(project_name)s < %(path)s/repository/data/psql/finish_init.sql' % env)
    

"""
Commands - django
"""

def syncdb():
	""" syncs the django database """
	
	print(green("Syncing %s database" % env.project))
	
	with virtualenv():
		with cd(env.code_root):
			run('./manage.py syncdb --settings=%s.settings_%s' % (env.project,env.environment))
			
def runserver():
	""" runs the project as a development server """


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



"""
Commands - miscellaneous
"""

    
def echo_host():
    """
    Echo the current host to the command line.
    """
    run('echo %(settings)s; echo %(hosts)s' % env)

"""
Deaths, destroyers of worlds
"""
def shiva_the_destroyer():
    """
    Remove all directories, databases, etc. associated with the application.
    """
    with settings(warn_only=True):
        run('rm -Rf %(code_root)s' % env)
        run('rm -Rf %s' % os.path.join(env.virtualenv_root, env.project))
        destroy_database()
        reboot()
       
"""
Utility functions (not to be called directly)
"""

@_contextmanager
def virtualenv():
	""" Wrapper function to ensure code is run under a virtual environment """

	venv_dir=os.path.join(env.virtualenv_root, env.project)
	activate='source ' + os.path.join(venv_dir,'bin','activate')

	with prefix(activate):
	    yield