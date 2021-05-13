from .base import *

DEBUG = True

if(DEBUG):
    INSTALLED_APPS = INSTALLED_APPS + INSTALLED_APPS_DEBUG
    MIDDLEWARE  = MIDDLEWARE_DEBUG + MIDDLEWARE 

#EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_USE_TLS = True
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_HOST_USER = os.environ["EMAIL_HOST_USER"]
EMAIL_HOST_PASSWORD = os.environ["EMAIL_HOST_PASSWORD"]
EMAIL_PORT = 587

CRISPY_FAIL_SILENTLY = not DEBUG

# EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
# EMAIL_USE_TLS = True
# EMAIL_HOST = 'smtp.gmail.com'
# EMAIL_HOST_USER = os.environ["EMAIL_HOST_USER"]
# EMAIL_HOST_PASSWORD = os.environ["EMAIL_HOST_PASSWORD"]
# EMAIL_PORT = 587

#Set to http for development purposes. Containers will be available on 50000-50019.
#Set to https for production purposes. Internal containers will be assigned ports 50000-50019, but will expect a webserverto provide ssl and upstream to them on ports 50020-50039.
CONTAINER_PROTOCOL = 'http'