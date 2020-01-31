from django.urls import path

from . import views

urlpatterns = [ 
    path('', views.index),
    path('manuscript_table', views.ManuscriptJson.as_view(), name="manuscript_table"), #TODO: Make sure accessing this directly doesn't reveal anything
    path('manuscript/create/', views.edit_manuscript),
    path('manuscript/edit/<int:id>', views.edit_manuscript),
    path('manuscript/addaccount/<int:id>', views.add_user),
    path('logout', views.logout_view),
]