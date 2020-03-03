from django.urls import path

from corere.main.views import datatables, main, users

urlpatterns = [ 
    path('', main.index),
    path('manuscript_table', datatables.ManuscriptJson.as_view(), name="manuscript_table"),
    path('manuscript/<int:manuscript_id>/submission_table', datatables.SubmissionJson.as_view(), name="submission_table"),
    path('manuscript/create/', main.edit_manuscript),
    path('manuscript/<int:id>/edit', main.edit_manuscript),
    path('manuscript/<int:id>/addauthor', users.add_author),
    path('manuscript/<int:id>/addcurator', users.add_curator),
    path('manuscript/<int:id>/deletecurator/<int:user_id>', users.delete_curator),
    path('manuscript/<int:id>/addverifier', users.add_verifier),
    path('manuscript/<int:id>/deleteverifier/<int:user_id>', users.delete_verifier),
    
    path('manuscript/<int:manuscript_id>/createsubmission', main.edit_submission),
    path('submission/<int:id>/edit', main.edit_submission),
    path('submission/<int:submission_id>/createcuration', main.edit_curation),
    path('curation/<int:id>/edit', main.edit_curation),
    path('submission/<int:submission_id>/createverification', main.edit_verification),
    path('verification/<int:id>/edit', main.edit_verification),

    path('logout', users.logout_view),
    path('account_associate_oauth/<str:key>', users.account_associate_oauth),
    path('account_user_details', users.account_user_details)
]