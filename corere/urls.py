"""corere URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from django.conf.urls import url, include
from django.conf import settings
from django.views.generic.base import RedirectView
import notifications.urls

handler400 = "corere.main.views.errors.handler400"
handler403 = "corere.main.views.errors.handler403"
handler404 = "corere.main.views.errors.handler404"
handler405 = "corere.main.views.errors.handler405"
handler500 = "corere.main.views.errors.handler500"

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("corere.main.urls")),
    url(r"^auth/", include("rest_framework_social_oauth2.urls")),  # Social OAuth2
    url(r"^invitations/", include("invitations.urls", namespace="invitations")),
    # url('^inbox/notifications/', RedirectView.as_view(url='/notifications')), #redirect notifications library url from their generic to our custom
    # url('^inbox/notifications/unread/', RedirectView.as_view(url='/notifications')), #redirect notifications library url from their generic to our custom
    # url('^notification_functions/', include(notifications.urls, namespace='notifications')),
    # TODO: Renaming this path broke badge updating, something in the library must me hardcoded. Maybe fork and fix?
    url("^inbox/notifications/", include(notifications.urls, namespace="notifications")),
    path("explorer/", include("explorer.urls")),
    # url(r'^select2/', include('django_select2.urls')), #if you use any "Auto" fields.
]

if settings.DEBUG and "debug_toolbar.middleware.DebugToolbarMiddleware" in settings.MIDDLEWARE:
    import debug_toolbar

    urlpatterns += [
        path("__debug__/", include(debug_toolbar.urls)),
    ]
