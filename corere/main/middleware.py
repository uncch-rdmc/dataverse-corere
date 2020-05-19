import threading

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