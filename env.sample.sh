### CORERE ###
# Used by Django to generate 
export UPLOAD_OUTPUT_PATH=
#This can reference the BASE_DIR in the settings file: DJANGO_LOG_PATH="BASE_DIR+/../../../../django-logs"
export DJANGO_LOG_DIRECTORY=
export DJANGO_SETTINGS_MODULE=corere.settings.development

### BINDERHUB ###
# Address of your Binderhub server
export BINDER_ADDR=

### GITLAB ###
# URL for commiting to gitlab repository from binderhub pod. Unused outside of prototype...
export GIT_CONFIG_URL="https://user:secret_token@gitlab_full_url/root/test.git/"
# URL for gitlab. Used by CORE-RE to download and commit to repository.
export GIT_LAB_URL=
# only "api/v4?" is supported at this stage
export GIT_API_VERSION="api/v4/"
# a list of emails (seperated by comma) to use to email changes in git repository.
export RECIPIENTS="email@email.com"

#For the Postgres DB
export POSTGRES_DB=corere

#Location for local file uploads (Manuscripts, etc)
export MEDIA_ROOT=