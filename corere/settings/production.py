from .base import *

DEBUG = False

# We shouldn't be installing the debug apps in production anyways, so this logic shouldn't get called
# Leaving it here to make it clear enabling debug will not enable debug apps and middleware
# if(DEBUG):
#     INSTALLED_APPS = INSTALLED_APPS + INSTALLED_APPS_DEBUG
#     MIDDLEWARE  = MIDDLEWARE_DEBUG + MIDDLEWARE 

ALLOWED_HOSTS = ['localhost', '127.0.0.1', '[::1]']