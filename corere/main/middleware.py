import threading, requests
from django.conf import settings

# from django.http import HttpResponseServerError #Http404
from django.shortcuts import render

local = threading.local()

# For passing the request directly to save for tracking
# See: https://www.agiliq.com/blog/2019/01/tracking-creator-of-django-objects/
# Also used for when we want to know the user when saving a model (Note etc)
class BaseMiddleware(object):
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        local.user = request.user
        response = self.get_response(request)
        return response


class WholeTaleOutageMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def process_exception(self, request, exception):
        if isinstance(exception, requests.exceptions.ConnectionError):
            if exception.request.url.startswith("https://girder." + settings.WHOLETALE_BASE_URL + "/api/v1"):
                # print(exception.request.url)
                return render(request, "main/500_wholetale.html", status=500)
        return None

    def __call__(self, request):
        response = self.get_response(request)
        return response
