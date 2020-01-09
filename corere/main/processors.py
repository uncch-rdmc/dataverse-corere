import os 

#To allow access to environment variables in templates
def export_vars(request):
    data = {}
    data['BINDER_ADDR_ENV'] = os.environ["BINDER_ADDR"]
    return data