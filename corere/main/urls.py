from django.urls import path

from . import views

urlpatterns = [ 
    path('', views.index),
    path('manuscript_table', views.ManuscriptJson.as_view(), name="manuscript_table"), #TODO: Make sure accessing this directly doesn't reveal anything
    path('create_manuscript', views.create_manuscript),
    path('logout', views.logout_view),
]