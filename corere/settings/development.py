from .base import *

DEBUG = True

if(DEBUG):
    INSTALLED_APPS = INSTALLED_APPS + INSTALLED_APPS_DEBUG
    MIDDLEWARE  = MIDDLEWARE_DEBUG + MIDDLEWARE 

ALLOWED_HOSTS = ['localhost', '127.0.0.1', '[::1]']

#Enabling this fakes all the gitlab calls so that development can be done without connection to a server
#Using this in production is not recommended as new accounts/manuscripts will be created without the needed gitlab infrastructure
DISABLE_GIT = True

# Database
DATABASES = {
    ## Can be enabled for quickest dev purposes
    # 'default': {
    #     'ENGINE': 'django.db.backends.sqlite3',
    #     'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
    # }
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': os.environ["POSTGRES_DB"],
        'USER': os.environ["POSTGRES_USER"],
        'PASSWORD': os.environ["POSTGRES_PASSWORD"],
        # 'HOST': os.environ["POSTGRES_HOST"], #unneeded except on GKE
        'PORT': '5432',
    }
}