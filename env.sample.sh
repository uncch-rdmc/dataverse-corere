### CORERE ###
#This can reference the BASE_DIR in the settings file: DJANGO_LOG_PATH="BASE_DIR+/../../../../django-logs"
export DJANGO_LOG_DIRECTORY=
export DJANGO_SETTINGS_MODULE=corere.settings.development

### GIT ###
# Absolute path where you want corere to store files (utilizing git). DO NOT use an existing git folder unless you want to risk wiping out your personal code.
export CORERE_GIT_FOLDER=

#For the Postgres DB
export POSTGRES_DB=corere
export POSTGRES_HOST=localhost

#Location for local file uploads (Manuscripts, etc). Unused currently
#export MEDIA_ROOT=

#Allowed hosts should be formatted as a comma separated set of strings. E.g. localhost,testserver:8000
export ALLOWED_HOSTS=*

#NOTE: Container address does not include the port, server address does (if needed)
export CONTAINER_ADDRESS="localhost"
export SERVER_ADDRESS="localhost:8000"

#Only used if using wholetale
export WHOLETALE_BASE_URL="wholetale.org"