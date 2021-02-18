from .base import *

DEBUG = True

if(DEBUG):
    INSTALLED_APPS = INSTALLED_APPS + INSTALLED_APPS_DEBUG
    MIDDLEWARE  = MIDDLEWARE_DEBUG + MIDDLEWARE 

ALLOWED_HOSTS = ['localhost', '127.0.0.1', '[::1]']

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