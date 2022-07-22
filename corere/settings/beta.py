from .base import *

# We enable debug for verbose errors, but we don't care about the other tools
DEBUG = False

# SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

# For nginx host passthru
USE_X_FORWARDED_HOST = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# We shouldn't be installing the debug apps in production anyways, so this logic shouldn't get called
# Leaving it here to make it clear enabling debug will not enable debug apps and middleware
# if(DEBUG):
#     INSTALLED_APPS = INSTALLED_APPS + INSTALLED_APPS_DEBUG
#     MIDDLEWARE  = MIDDLEWARE_DEBUG + MIDDLEWARE

# These settings are based upon gmail, switch to your prefered smtp service
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_USE_TLS = True
EMAIL_HOST = "smtp.gmail.com"
EMAIL_HOST_USER = os.environ["EMAIL_HOST_USER"]
EMAIL_HOST_PASSWORD = os.environ["EMAIL_HOST_PASSWORD"]
EMAIL_PORT = 587

COMPRESS_OFFLINE = True
COMPRESS_ENABLED = False

# Set to http for development purposes. Containers will be available on 50020-50039.
# Set to https for production purposes. Internal containers will be assigned ports 50020-50039, but will expect a webserver to provide ssl and upstream to them via ports 50000-50019.
CONTAINER_PROTOCOL = "https"
CONTAINER_TO_CORERE_ADDRESS = os.environ["SERVER_ADDRESS"]

SKIP_DOCKER = False
SKIP_EDITION = False

# CONTAINER_DRIVER = 'local-docker'
CONTAINER_DRIVER = "wholetale"

CURATION_GROUP_EMAIL = os.environ["CURATION_GROUP_EMAIL"]