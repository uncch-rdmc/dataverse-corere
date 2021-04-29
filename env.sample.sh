### CORERE ###
# Used by Django to generate 
export UPLOAD_OUTPUT_PATH=
#This can reference the BASE_DIR in the settings file: DJANGO_LOG_PATH="BASE_DIR+/../../../../django-logs"
export DJANGO_LOG_DIRECTORY=
export DJANGO_SETTINGS_MODULE=corere.settings.development

### GIT ###
# Absolute path where you want corere to store files (utilizing git). DO NOT use an existing git folder unless you want to risk wiping out your personal code.
export CORERE_GIT_FOLDER=

#For the Postgres DB
export POSTGRES_DB=corere
export POSTGRES_HOST=localhost

#Location for local file uploads (Manuscripts, etc)
export MEDIA_ROOT=