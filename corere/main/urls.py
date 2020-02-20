from django.urls import path

from corere.main.views import datatables, main, users

urlpatterns = [ 
    path('', main.index),
    path('manuscript_table', datatables.ManuscriptJson.as_view(), name="manuscript_table"), #TODO: Make sure accessing this directly doesn't reveal anything
    path('manuscript/<int:manuscript_id>/submission_table', datatables.SubmissionJson.as_view(), name="submission_table"), #TODO: Make sure accessing this directly doesn't reveal anything
    path('manuscript/create/', main.edit_manuscript),
    path('manuscript/<int:id>/edit', main.edit_manuscript),
    path('manuscript/<int:id>/addauthor', users.add_author),
    path('manuscript/<int:id>/addcurator', users.add_curator),
    path('manuscript/<int:id>/addverifier', users.add_verifier),
    path('logout', users.logout_view),
    path('account_associate_oauth/<str:key>', users.account_associate_oauth),
    path('account_user_details', users.account_user_details)
]