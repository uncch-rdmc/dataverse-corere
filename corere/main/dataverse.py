import pyDataverse.api as pyd
from django.conf import settings

def test_py_dv():
    #MetricsApi(base_url, api_token=None
    # print(pyd.__dict__)
    #metrics = pyd.MetricsApi(settings.DATAVERSE_BASE_URL, api_token=settings.DATAVERSE_API_KEY) #{"status":"ERROR","message":"queryParameter User-Agent not supported for this endpont"}
    native_api = pyd.NativeApi(settings.DATAVERSE_BASE_URL, api_token=settings.DATAVERSE_API_KEY)
    #This is very slow
    print(str(native_api.get_children()))
