from .base import *

DEBUG = False

# We shouldn't be installing the debug apps in production anyways, so this logic shouldn't get called
# Leaving it here to make it clear enabling debug will not enable debug apps and middleware
# if(DEBUG):
#     INSTALLED_APPS = INSTALLED_APPS + INSTALLED_APPS_DEBUG
#     MIDDLEWARE  = MIDDLEWARE_DEBUG + MIDDLEWARE 

EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

#These settings are based upon gmail, switch to your prefered smtp service
# EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
# EMAIL_USE_TLS = True
# EMAIL_HOST = 'smtp.gmail.com'
# EMAIL_HOST_USER = os.environ["EMAIL_HOST_USER"]
# EMAIL_HOST_PASSWORD = os.environ["EMAIL_HOST_PASSWORD"]
# EMAIL_PORT = 587

COMPRESS_OFFLINE = True
COMPRESS_ENABLED = False

CONTAINER_PROTOCOL = 'https'