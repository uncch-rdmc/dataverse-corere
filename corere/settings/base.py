import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SECRET_KEY = os.environ["DJANGO_SECRET_KEY"]
# TODO: Test removing this setting at some point and see how many warnings we still get. Hopefully other packages will fix their defaults. We should also explore setting our autofield to BigAutoField.
DEFAULT_AUTO_FIELD = "django.db.models.AutoField"

LOGIN_URL = "/"
LOGIN_REDIRECT_URL = "/?login=true"
LOGOUT_REDIRECT_URL = "/"

# MEDIA_ROOT = os.environ["MEDIA_ROOT"]
# MEDIA_URL

ALLOWED_HOSTS = os.environ.get("ALLOWED_HOSTS", "").split(",")
# NOTE: Container address does not include the port, server address does (if needed).
CONTAINER_ADDRESS = os.environ["CONTAINER_ADDRESS"]
SERVER_ADDRESS = os.environ["SERVER_ADDRESS"]

# Invitation related
SITE_ID = 1
# INVITATION_MODEL = 'main.CorereInvitation' #Instead of using this we just reference CorereInvitation directly
INVITATIONS_EMAIL_MAX_LENGTH = 200
INVITATIONS_SIGNUP_REDIRECT = "/account_associate_oauth"
# INVITATIONS_ACCEPT_INVITE_AFTER_SIGNUP = True #TODO: this should allow us keep an invitation open until signup completes, but adding it errors

GIT_ROOT = os.environ["CORERE_GIT_FOLDER"]

DOCKER_GEN_TAG = "jupyter-corere"
DOCKER_OAUTH_PROXY_BASE_IMAGE = "bitnami/oauth2-proxy:7.1.2"

# Used to build OAuth2Proxy, which requires a file to be passed to store permitted email addresses.
DOCKER_BUILD_FOLDER = "/tmp"

# Application definition
INSTALLED_APPS = [
    "corere.apps.wholetale",
    "corere.apps.file_datatable",
    "django.forms",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.sites",  # added for invitations
    "crispy_forms",
    "invitations",
    "notifications",
    "oauth2_provider",
    "social_django",
    "rest_framework_social_oauth2",
    "compressor",
    "guardian",
    "simple_history",
    "corere.main",
    "explorer",
]

FORM_RENDERER = "django.forms.renderers.TemplatesSetting"  # to allow our custom override of default widgets

INSTALLED_APPS_DEBUG = [
    "django_fsm",  # Library is used in prod, but only has to be installed in dev for visualizing the state diagram
    "django_extensions",
    "debug_toolbar",
    "sslserver",
]

# Note that middleware order matters https://django-debug-toolbar.readthedocs.io/en/latest/installation.html#enabling-middleware
MIDDLEWARE_DEBUG = ["debug_toolbar.middleware.DebugToolbarMiddleware"]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "simple_history.middleware.HistoryRequestMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "crequest.middleware.CrequestMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "corere.main.middleware.WholeTaleOutageMiddleware",
    "corere.main.middleware.BaseMiddleware",
    "corere.main.utils.UserAlreadyAssociatedMiddleware",
]

# To have django-debug-toolbar show
INTERNAL_IPS = [
    "127.0.0.1",
]

ROOT_URLCONF = "corere.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [os.path.join(BASE_DIR, "main/templates"), "/corere/apps/file_datatable/templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "social_django.context_processors.backends",
                "social_django.context_processors.login_redirect",
            ],
        },
    },
]

WSGI_APPLICATION = "corere.wsgi.application"

AUTH_USER_MODEL = "main.User"

# Database
DATABASES = {
    ## Can be enabled for quickest dev purposes
    # 'default': {
    #     'ENGINE': 'django.db.backends.sqlite3',
    #     'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
    # }
    "default": {
        "ENGINE": "django.db.backends.postgresql_psycopg2",
        "NAME": os.environ["POSTGRES_DB"],
        "USER": os.environ["POSTGRES_USER"],
        "PASSWORD": os.environ["POSTGRES_PASSWORD"],
        "HOST": os.environ["POSTGRES_HOST"],  # TODO: is this needed?
        "PORT": "5432",
        "ATOMIC_REQUESTS": True,
    },
    # Used for admin sql queries
    "readonly": {
        "ENGINE": "django.db.backends.postgresql_psycopg2",
        "NAME": os.environ["POSTGRES_DB"],
        "USER": os.environ["POSTGRES_USER"],
        "PASSWORD": os.environ["POSTGRES_PASSWORD"],
        "HOST": os.environ["POSTGRES_HOST"],
        "PORT": "5432",
        "OPTIONS": {"options": "-c default_transaction_read_only=on"},
    },
}

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "oauth2_provider.contrib.rest_framework.OAuth2Authentication",  # django-oauth-toolkit >= 1.0.0
        "rest_framework_social_oauth2.authentication.SocialAuthentication",
    ),
}

AUTHENTICATION_BACKENDS = (
    "social_core.backends.globus.GlobusOpenIdConnect",
    # 'social_core.backends.google.GoogleOAuth2',
    # 'social_core.backends.github.GithubOAuth2',
    "guardian.backends.ObjectPermissionBackend",
    "django.contrib.auth.backends.ModelBackend",  # Standard django auth, used for admin
)

# Django Model Auth Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "django_file": {
            "level": "INFO",
            "class": "logging.handlers.TimedRotatingFileHandler",
            "formatter": "normal",
            "filename": os.environ["DJANGO_LOG_DIRECTORY"] + "/django.log",
            "interval": 1,
        },
        "file": {
            "level": "DEBUG",
            "class": "logging.handlers.TimedRotatingFileHandler",
            "formatter": "normal",
            "filename": os.environ["DJANGO_LOG_DIRECTORY"] + "/corere.log",
            "interval": 1,
        },
    },
    "loggers": {
        "django": {
            "handlers": ["django_file"],
            "level": "INFO",
            "propagate": True,
        },
        "corere": {
            "handlers": ["file"],
            "level": "INFO",
            "propagate": True,
        },
        "dataverse": {
            "handlers": ["file"],
            "level": "DEBUG",
            "propagate": True,
        },
    },
    "formatters": {
        "normal": {"format": "%(asctime)s %(levelname)-8s [%(module)s:%(lineno).3d] %(message)s", "datefmt": "%Y-%m-%d %H:%M:%S"},
    },
}

# Internationalization
LANGUAGE_CODE = "en"
TIME_ZONE = "UTC"
USE_I18N = True
USE_L10N = True
USE_TZ = True
LOCALE_PATHS = (os.path.join(BASE_DIR, "locale"),)

STATICFILES_FINDERS = (
    "django.contrib.staticfiles.finders.FileSystemFinder",
    "django.contrib.staticfiles.finders.AppDirectoriesFinder",
    # other finders..
    "compressor.finders.CompressorFinder",
)

# Used by compressor for SASS/SCSS
COMPRESS_PRECOMPILERS = (("text/x-scss", "django_libsass.SassCompiler"),)

# Static files (CSS, JavaScript, Images)
STATIC_ROOT = os.path.join(BASE_DIR, "static")
STATIC_URL = "/static/"

# More Social Auth Configuration
DRFSO2_PROPRIETARY_BACKEND_NAME = "Corere"

SOCIAL_AUTH_PIPELINE = (
    #'social_core.pipeline.social_auth.social_details',
    "social_core.pipeline.social_auth.social_uid",
    "social_core.pipeline.social_auth.auth_allowed",
    "social_core.pipeline.social_auth.social_user",
    "corere.main.utils.social_pipeline_return_session_user",
    "social_core.pipeline.user.get_username",
    "social_core.pipeline.social_auth.associate_user"
    # 'social_core.pipeline.social_auth.load_extra_data',
    #'social_core.pipeline.user.user_details',
)

# NOTE: As part of glbous registration, we currently have pre-reserve ports 50020-50039 on our ip (for the oauth redirect url). This is for the jupyter notebooks. It includes the /tree path

# Social Auth: Globus configuration
SOCIAL_AUTH_GLOBUS_KEY = os.environ["SOCIAL_AUTH_GLOBUS_OAUTH2_KEY"]
SOCIAL_AUTH_GLOBUS_SECRET = os.environ["SOCIAL_AUTH_GLOBUS_OAUTH2_SECRET"]
SOCIAL_AUTH_GLOBUS_AUTH_EXTRA_ARGUMENTS = {
    "access_type": "offline",
}
SOCIAL_AUTH_NEW_USER_REDIRECT_URL = "/account_complete_oauth/"
SOCIAL_AUTH_NEW_ASSOCIATION_REDIRECT_URL = "/account_complete_oauth/"

OAUTHPROXY_COOKIE_SECRET = os.environ["OAUTHPROXY_COOKIE_SECRET"]

CRISPY_TEMPLATE_PACK = "bootstrap4"

SIMPLE_HISTORY_REVERT_DISABLED = True

EXPLORER_CONNECTIONS = {"Default": "readonly"}
EXPLORER_DEFAULT_CONNECTION = "readonly"
# EXPLORER_NO_PERMISSION_VIEW = 'explorer.views.auth.safe_login_view_wrapper'
EXPLORER_SQL_BLACKLIST = (
    "ALTER",
    "CREATE TABLE",
    "DELETE",
    "DROP",
    "GRANT",
    "INSERT INTO",
    "OWNER TO",
    "RENAME ",
    #'REPLACE',
    "SCHEMA",
    "TRUNCATE",
    "UPDATE",
)

WHOLETALE_BASE_URL = os.environ["WHOLETALE_BASE_URL"]
WHOLETALE_ADMIN_GIRDER_API_KEY = os.environ["WHOLETALE_ADMIN_GIRDER_API_KEY"]

# DATAVERSE_BASE_URL = os.environ["DATAVERSE_BASE_URL"]
# DATAVERSE_API_KEY = os.environ["DATAVERSE_API_KEY"]

# CSRF_COOKIE_SAMESITE = 'None'
##Enabling this setting causes social auth to break
# SESSION_COOKIE_SAMESITE = 'None'

SKIP_EDITION = False

# This is a selenium-only flag, do not use in a real environment
SKIP_GIT = False
