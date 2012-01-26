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
        #load_data()
        install_requirements()
        setup_apache()
        syncdb()
        migratedb()
        
   
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
	sudo('WORKON_HOME=%s' % (env.virtualenv_root) + ' && ' + 'source /usr/local/bin/virtualenvwrapper.sh && ' + 'mkvirtualenv --no-site-packages %s' % (env.project))


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
            
            if line[0] != '#' and line[0].strip() !="":
                run("pip install %s" % (line))



"""
Commands - apache
"""
def setup_apache():
	
	print(green('Updating apache settings'))
	
	create_apache_conf_files()
	update_apache_conf()
	
def update_apache_conf():
	""" upload apache configuration to remote host """

	require('root', provided_by=('staging', 'production'))

	print(red('moving conf files'))

	conf_dest = os.path.join(env.apacheconfig, 'sites','%(servername)s.conf' % env)
	conf=os.path.join(env.code_root,'fabtools','install','%s.conf' % env.environment)

	wsgi=os.path.join(env.code_root,'fabtools','install','%s.wsgi' % env.environment)
	wsgi_dest=os.path.join(env.code_root,'apache','%s.wsgi' % env.environment)

	run('mkdir -p %s' % os.path.join(env.code_root,'apache'))
	run('cp %s %s' % (wsgi,wsgi_dest))
	run('cp %s %s' % (conf,conf_dest))
	reboot()


def configtest():    
    """ test Apache configuration """
    require('root', provided_by=('staging', 'production'))
    run('apachectl configtest')


def reboot():    
	""" reload Apache on remote host """

	print(red('Reloading apache'))

	require('root', provided_by=('staging', 'production'))
	run('sudo apachectl restart')



def create_apache_conf_files():
	""" creates apache conf files from templates in ./install/ """

	print(green('Creating apache conf files from templates'))
	
	conf_template=os.path.join(env.code_root,'fabtools','install','template.conf')
	
	conf_template=get(conf_template)[0]
	
	conf=os.path.join(env.code_root,'fabtools','install','%s.conf' % env.environment)
	
	wsgi_template=os.path.join(env.code_root,'fabtools','install','template.wsgi')
	wsgi=os.path.join(env.code_root,'fabtools','install','%s.wsgi' % env.environment)
	wsgi_template=get(wsgi_template)[0]
	
	r={ 'project':env.project,
		'environment':env.environment,
		'servername':env.servername,
		'home':env.home,
		'certificate-file':os.path.join(env.apacheconfig,'ssl-certificate.conf')
	}
	
	print(red('Replacing %s and saving as %s' % (conf_template,conf)))
	_open_file_and_replace(conf_template,conf_template + ".out",r)
	put(conf_template+ ".out", conf, mode=0755)
	
	print(red('Replacing %s and saving as %s' % (conf_template,conf)))
	_open_file_and_replace(wsgi_template,wsgi_template+".out",r)
	put(wsgi_template+ ".out", wsgi, mode=0755)
	
	
	local('rm -r %s' % env.host)

	




"""
Commands - deployment
"""
def deploy():
    """
    Deploy the latest version of the site to the server and restart Apache2.
    
    Does not perform the functions of load_new_data().
    """
   
    
    with settings(warn_only=True):
        maintenance_up()
        
    checkout_latest()
    migrate()
    collectstatic()
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
    pass
    #run('cd %(repo_path)s; python gzip_assets.py' % env)

    
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

    
    maintenance_up()
    checkout_latest()
    git_reset(commit_id)
    gzip_assets()
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
    
    create_sql="create database %(db)s;" % env
    user_sql="grant all privileges on %(db)s.* to '%(db_user)s'@'%%' identified by '%(db_password)s';" % env
    
    sql=create_sql+user_sql
   
    run('echo "%s" | mysql -uroot -p'  % (sql))
    
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
    with settings(warn_only=True):
         run('mysql -u%(db_user)s -p%(db_password)s %(db)s < %(db_backup)s' % env)
    #run('psql -q %(project_name)s < %(path)s/repository/data/psql/dump.sql' % env)
    #run('psql -q %(project_name)s < %(path)s/repository/data/psql/finish_init.sql' % env)
    
def dump_data():
    """
    Creates a database backup
    """
    
    run('mysqldump -u%(db_user)s -p%(db_password)s %(db)s > %(db_backup)s' % env)

"""
Commands - django
"""
def manage(cmd):
	""" runs django command cmd """


	if env.environment == 'development':
		local('./manage.py %s --settings=%s.settings_%s' % (cmd,env.project,env.environment))
		return

	with virtualenv():
		with cd(env.code_root):
			run('./manage.py %s --settings=%s.settings_%s' % (cmd,env.project,env.environment))
			
def syncdb():
	""" syncs the django database """
	
	print(green("Syncing %s database" % env.project))
	
	manage('syncdb')



def runserver():
    """ runs the project as a development server """


    print(green('Running development server.  Access at http://127.0.0.1:%s' % env.serverport))

    manage('runserver 0.0.0.0:%s' % env.serverport)

def collectstatic():
    """ collects static files """

    print(green('Collecting static files'))

    manage('collectstatic')
 
def migrate():
    """ migrates apps using south """

    print(green('Migrating apps'))

    manage('migrate --all')   


def shell():
    """ migrates apps using south """

    manage('shell')

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
	    
def _open_file_and_replace(src,dest,replace_dict):
	""" replaces <key> in src with val from key,val of replace_dict with supplied values and saves as dest 
	"""

	f=open(src,'r')
	o=open(dest,'w')

	for line in f.readlines():
		for k,r in replace_dict.iteritems():
			line=line.replace('<%s>' % k,'%s' % r)

		o.write(line+"\n")

	f.close()
	o.close()