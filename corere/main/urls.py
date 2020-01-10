from django.urls import path

from . import views

urlpatterns = [ 
    path('', views.index),
    path('index', views.index),
    path('create_import', views.create_or_import),
    path('create', views.create_catalog),
    path('load', views.load),
    path('logout', views.logout_view),

    path('create_import_init', views.create_import_init),

    path('uploadfiles', views.uploadfiles),

]