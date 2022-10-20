#Make sure this is greater than 50 characters in production
export DJANGO_SECRET_KEY=

### SOCIAL AUTH ###
# Values used for Globus OAuth2.
export SOCIAL_AUTH_GLOBUS_OAUTH2_KEY=
export SOCIAL_AUTH_GLOBUS_OAUTH2_SECRET=

export POSTGRES_USER=
export POSTGRES_PASSWORD=

export EMAIL_HOST_USER=
export EMAIL_HOST_PASSWORD=

# After installation/change, call manage.py createsuperuser --noinput to enable superuser
export DJANGO_SUPERUSER_USERNAME=
export DJANGO_SUPERUSER_EMAIL=
export DJANGO_SUPERUSER_PASSWORD=

export OAUTHPROXY_COOKIE_SECRET=

#Only used if using wholetale, for administrative tasks
export WHOLETALE_ADMIN_GIRDER_API_KEY=""