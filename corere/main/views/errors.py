import logging
from django.shortcuts import render
logger = logging.getLogger(__name__)

def handler400(request, exception, template_name="main/400.html"): 
    response = render(request, template_name) 
    response.status_code = 400
    return response

def handler403(request, exception, template_name="main/403.html"): 
    response = render(request, template_name) 
    response.status_code = 403
    return response

def handler404(request, exception, template_name="main/404.html"): 
    response = render(request, template_name) 
    response.status_code = 404
    return response

def handler405(request, exception, template_name="main/405.html"): 
    response = render(request, template_name) 
    response.status_code = 405
    return response

def handler500(request, template_name="main/500.html"): 
    response = render(request, template_name) 
    response.status_code = 500
    return response