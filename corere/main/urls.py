from django.urls import path

from corere.main.views import datatables, main, users


urlpatterns = [ 
    path('', main.index),
    path('manuscript_table', datatables.ManuscriptJson.as_view(), name="manuscript_table"),
    path('manuscript/<int:manuscript_id>/submission_table', datatables.SubmissionJson.as_view(), name="submission_table"),
    path('manuscript/create', main.ManuscriptCreateView.as_view()),
    path('manuscript/<int:id>/edit', main.ManuscriptEditView.as_view()),
    path('manuscript/<int:id>/editfiles', main.ManuscriptEditFilesView.as_view()),
    path('manuscript/<int:id>/view', main.ManuscriptReadView.as_view()),
    path('manuscript/<int:id>/addauthor', users.add_author),
    path('manuscript/<int:id>/addcurator', users.add_curator),
    path('manuscript/<int:id>/deletecurator/<int:user_id>', users.delete_curator),
    path('manuscript/<int:id>/addverifier', users.add_verifier),
    path('manuscript/<int:id>/deleteverifier/<int:user_id>', users.delete_verifier),
    path('manuscript/<int:manuscript_id>/createsubmission', main.SubmissionCreateView.as_view()),

    path('submission/<int:id>/edit', main.SubmissionEditView.as_view()),
    path('submission/<int:id>/view', main.SubmissionReadView.as_view()),
    path('submission/<int:submission_id>/createcuration', main.CurationCreateView.as_view()),
    path('submission/<int:submission_id>/createverification', main.VerificationCreateView.as_view()),
    path('submission/<int:submission_id>/createnote', main.edit_note),
    path('submission/<int:submission_id>/editnote/<int:id>', main.edit_note),
    path('submission/<int:submission_id>/deletenote/<int:id>', main.delete_note),

    path('curation/<int:id>/edit', main.CurationEditView.as_view()),
    path('curation/<int:id>/view', main.CurationReadView.as_view()),
    path('curation/<int:curation_id>/createnote', main.edit_note),
    path('curation/<int:curation_id>/editnote/<int:id>', main.edit_note),
    path('curation/<int:curation_id>/deletenote/<int:id>', main.delete_note),

    path('verification/<int:id>/edit', main.VerificationEditView.as_view()),
    path('verification/<int:id>/view', main.VerificationReadView.as_view()),
    path('verification/<int:verification_id>/createnote', main.edit_note),
    path('verification/<int:verification_id>/editnote/<int:id>', main.edit_note),
    path('verification/<int:verification_id>/deletenote/<int:id>', main.delete_note),

    path('logout', users.logout_view),
    path('account_associate_oauth/<str:key>', users.account_associate_oauth),
    path('account_user_details', users.account_user_details),
]