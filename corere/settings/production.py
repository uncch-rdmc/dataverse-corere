from .base import *

DEBUG = False

# We shouldn't be installing the debug apps in production anyways, so this logic shouldn't get called
# Leaving it here to make it clear enabling debug will not enable debug apps and middleware
# if(DEBUG):
#     INSTALLED_APPS = INSTALLED_APPS + INSTALLED_APPS_DEBUG
#     MIDDLEWARE  = MIDDLEWARE_DEBUG + MIDDLEWARE 

ALLOWED_HOSTS = ['localhost', '0.0.0.0', '[::1]', '*'] #TODO: REMOVE *

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
        'HOST': os.environ["DB_SERVICE_HOST"],
        'PORT': '5432',
    }
}