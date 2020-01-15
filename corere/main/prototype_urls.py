from django.urls import path

from . import prototype_views

urlpatterns = [ 
    path('', prototype_views.index),
    path('index', prototype_views.index),
    path('create_import', prototype_views.create_or_import),
    path('create', prototype_views.create_catalog),
    path('load', prototype_views.load),
    path('logout', prototype_views.logout_view),

    path('create_import_init', prototype_views.create_import_init),

    path('uploadfiles', prototype_views.uploadfiles),

]