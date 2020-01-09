### CORERE ###
# Used by Django to generate 
export DJANGO_SECRET_KEY=
export UPLOAD_OUTPUT_PATH=

### BINDERHUB ###
# Address of your Binderhub server
export BINDER_ADDR=

### GITLAB ###
# URL for commiting to gitlab repository from binderhub pod.
export GIT_CONFIG_URL="https://user:secret_token@gitlab_full_url/root/test.git/"
# URL for gitlab. Used by CORE-RE to download and commit to repository.
export GIT_LAB_URL=
# only "api/v4?" is supported at this stage
export GIT_API_VERSION="api/v4/"
# private token used by CORE-RE server that has global access.
export GIT_PRIVATE_TOKEN=
# a list of emails (seperated by comma) to use to email changes in git repository.
export RECIPIENTS="email@email.com"

### SOCIAL AUTH ###
# Values used for Google OAuth2. See https://python-social-auth.readthedocs.io/en/latest/backends/google.html
export SOCIAL_AUTH_GOOGLE_OAUTH2_KEY=
export SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET=