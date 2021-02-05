import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SECRET_KEY = os.environ["DJANGO_SECRET_KEY"]

LOGIN_URL = '/'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/'

MEDIA_ROOT = os.environ["MEDIA_ROOT"]
#MEDIA_URL

#Invitation related
SITE_ID = 1
INVITATIONS_EMAIL_MAX_LENGTH = 200
INVITATIONS_SIGNUP_REDIRECT = '/account_associate_oauth'

GIT_ROOT = os.environ["CORERE_GIT_FOLDER"]

#TODO: Delete if we switch to local git. Also delete from env. Not sure about RECIPIENTS.
#P.S.: What are we using MEDIA_ROOT in env.sh for?
#CUSTOM CORERE
GIT_CONFIG_URL = os.environ["GIT_CONFIG_URL"]
GIT_LAB_URL = os.environ["GIT_LAB_URL"]
GIT_API_VERSION = os.environ["GIT_API_VERSION"]
GIT_PRIVATE_ADMIN_TOKEN = os.environ["GIT_PRIVATE_ADMIN_TOKEN"]
RECIPIENTS = os.environ["RECIPIENTS"]

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sites', #added for invitations
    'crispy_forms',
    'invitations',
    'notifications',
    'oauth2_provider',
    'social_django',
    'rest_framework_social_oauth2',
    'compressor',
    'guardian',
    'simple_history',
    'corere.main',
]

INSTALLED_APPS_DEBUG = [
    'django_fsm', #Library is used in prod, but only has to be installed in dev for visualizing the state diagram
    'django_extensions',
    'debug_toolbar',
]

# Note that middleware order matters https://django-debug-toolbar.readthedocs.io/en/latest/installation.html#enabling-middleware
MIDDLEWARE_DEBUG = [
    'debug_toolbar.middleware.DebugToolbarMiddleware'
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'simple_history.middleware.HistoryRequestMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'crequest.middleware.CrequestMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'corere.main.middleware.BaseMiddleware',
]

#To have django-debug-toolbar show
INTERNAL_IPS = [
    '127.0.0.1',
]

ROOT_URLCONF = 'corere.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'social_django.context_processors.backends',
                'social_django.context_processors.login_redirect',
                'corere.main.processors.export_vars',
            ],
        },
    },
]

WSGI_APPLICATION = 'corere.wsgi.application'

AUTH_USER_MODEL = 'main.User'

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
        'HOST': os.environ["POSTGRES_HOST"], #TODO: is this needed?
        'PORT': '5432',
    }
}

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'oauth2_provider.contrib.rest_framework.OAuth2Authentication',  # django-oauth-toolkit >= 1.0.0
        'rest_framework_social_oauth2.authentication.SocialAuthentication',
    ),
}

AUTHENTICATION_BACKENDS = (
    'social_core.backends.google.GoogleOAuth2',
    'social_core.backends.github.GithubOAuth2',
    'guardian.backends.ObjectPermissionBackend',
    'django.contrib.auth.backends.ModelBackend', #Standard django auth, used for admin
)

# Django Model Auth Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'django_file': {
            'level': 'DEBUG',
            'class': 'logging.handlers.TimedRotatingFileHandler',
            'formatter': 'normal',
            'filename': os.environ["DJANGO_LOG_DIRECTORY"] + "/django.log",
            'interval': 1,
        },      
        'file': {
            'level': 'DEBUG',
            'class': 'logging.handlers.TimedRotatingFileHandler',
            'formatter': 'normal',
            'filename': os.environ["DJANGO_LOG_DIRECTORY"] + "/corere.log",
            'interval': 1,
        },         
    },
    'loggers': {
        'django': {
            'handlers': ['django_file'],
            'level': 'DEBUG',
            'propagate': True,
        },
        'corere': {
            'handlers': ['file'],
            'level': 'DEBUG',
            'propagate': True,
        },
    },
    'formatters': {
        'normal': {
            'format': '%(asctime)s %(levelname)-8s [%(module)s:%(lineno).3d] %(message)s',
            'datefmt': '%Y-%m-%d %H:%M:%S'
        },
    }
}

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = False
USE_L10N = False
USE_TZ = True

STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
    # other finders..
    'compressor.finders.CompressorFinder',
)

# Used by compressor for SASS/SCSS
COMPRESS_PRECOMPILERS = (
    ('text/x-scss', 'django_libsass.SassCompiler'),
)

# Static files (CSS, JavaScript, Images)
STATIC_ROOT = os.path.join(BASE_DIR,'static')
STATIC_URL = '/static/'

#More Social Auth Configuration
DRFSO2_PROPRIETARY_BACKEND_NAME =  "Corere"

SOCIAL_AUTH_PIPELINE = (
    'social_core.pipeline.social_auth.social_details',
    'social_core.pipeline.social_auth.social_uid',
    'social_core.pipeline.social_auth.auth_allowed',
    'social_core.pipeline.social_auth.social_user',
    'corere.main.utils.social_pipeline_return_session_user',
    'social_core.pipeline.user.get_username',
    'social_core.pipeline.social_auth.associate_user',
    'social_core.pipeline.social_auth.load_extra_data',
    'social_core.pipeline.user.user_details',
)

# Social Auth: Google configuration
SOCIAL_AUTH_GOOGLE_OAUTH2_KEY = os.environ["SOCIAL_AUTH_GOOGLE_OAUTH2_KEY"]
SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET = os.environ["SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET"]
SOCIAL_AUTH_GOOGLE_OAUTH2_SCOPE = [
    'https://www.googleapis.com/auth/userinfo.email',
    'https://www.googleapis.com/auth/userinfo.profile',
]

# Social Auth: Github configuration
SOCIAL_AUTH_GITHUB_KEY = os.environ["SOCIAL_AUTH_GITHUB_OAUTH2_KEY"]
SOCIAL_AUTH_GITHUB_SECRET = os.environ["SOCIAL_AUTH_GITHUB_OAUTH2_SECRET"]

CRISPY_TEMPLATE_PACK = 'bootstrap4'

SIMPLE_HISTORY_REVERT_DISABLED=True