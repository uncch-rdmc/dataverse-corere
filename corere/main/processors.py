import os 

#To allow access to environment variables in templates
def export_vars(request):
    data = {}
    data['BINDER_ADDR_ENV'] = os.environ["BINDER_ADDR"]
    data['GIT_CONFIG_URL_ENV'] = os.environ["GIT_CONFIG_URL"]
    data['GIT_LAB_URL_ENV'] = os.environ["GIT_LAB_URL"]
    data['GIT_API_VERSION_ENV'] = os.environ["GIT_API_VERSION"]
    data['GIT_PRIVATE_TOKEN_ENV_MAD_DELETE'] = os.environ["GIT_PRIVATE_TOKEN"]
    return data